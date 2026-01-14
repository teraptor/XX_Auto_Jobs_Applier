#!/bin/bash
#
# Test Docker setup for XX Auto Jobs Applier
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}Testing XX Auto Jobs Applier Docker Setup${NC}"
echo -e "${BLUE}===============================================${NC}\n"

# Test function
test_service() {
    local service=$1
    local test_command=$2
    local description=$3

    echo -n "Testing $description... "
    if eval $test_command > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${YELLOW}Step 1: Checking Docker services${NC}"

# Check if Docker is running
test_service "Docker" "docker info" "Docker daemon" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Check if docker-compose is available
test_service "Docker Compose" "docker-compose version" "Docker Compose" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

echo -e "\n${YELLOW}Step 2: Checking running services${NC}"

# Check PostgreSQL
test_service "PostgreSQL" "docker-compose exec -T postgres pg_isready -U postgres" "PostgreSQL connection" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Check Redis
test_service "Redis" "docker-compose exec -T redis redis-cli ping" "Redis connection" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Check API health
test_service "API" "curl -f -s http://localhost:8000/health" "API health endpoint" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

echo -e "\n${YELLOW}Step 3: Testing API endpoints${NC}"

# Test root endpoint
test_service "API Root" "curl -f -s http://localhost:8000/" "API root endpoint" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Test metrics endpoint
test_service "Metrics" "curl -f -s http://localhost:9090/metrics" "Prometheus metrics" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Test queue stats
test_service "Queue Stats" "curl -f -s http://localhost:8000/queue/stats" "Queue statistics" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Test pool status
test_service "Browser Pool" "curl -f -s http://localhost:8000/pool/status" "Browser pool status" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

echo -e "\n${YELLOW}Step 4: Database connectivity${NC}"

# Test database tables
test_service "Database Tables" "docker-compose exec -T postgres psql -U postgres -d autoapplyer -c '\dt'" "Database tables exist" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

echo -e "\n${YELLOW}Step 5: Worker status${NC}"

# Check if workers are running
test_service "Worker 1" "docker-compose ps worker-1 | grep Up" "Worker 1 running" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))
test_service "Worker 2" "docker-compose ps worker-2 | grep Up" "Worker 2 running" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

echo -e "\n${YELLOW}Step 6: Redis queue test${NC}"

# Create a test task
cat > /tmp/test_redis.py << 'EOF'
import redis
import json
import uuid
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Create test task
task_id = str(uuid.uuid4())
task = {
    "task_id": task_id,
    "tenant_id": "test-tenant",
    "user_id": "test-user",
    "type": "test",
    "created_at": datetime.utcnow().isoformat()
}

# Push to queue
r.lpush("tasks:pending", json.dumps(task))
print(f"Task created: {task_id}")

# Check queue length
queue_length = r.llen("tasks:pending")
print(f"Queue length: {queue_length}")

# Clean up test task
r.rpop("tasks:pending")
EOF

if docker run --rm --network host -v /tmp:/tmp python:3.11-slim sh -c "pip install redis && python /tmp/test_redis.py" > /dev/null 2>&1; then
    echo -e "Redis queue test... ${GREEN}✓ Passed${NC}"
    ((TESTS_PASSED++))
else
    echo -e "Redis queue test... ${RED}✗ Failed${NC}"
    ((TESTS_FAILED++))
fi

rm -f /tmp/test_redis.py

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed! Docker setup is working correctly.${NC}"

    echo -e "\n${YELLOW}Optional: Run end-to-end test${NC}"
    echo "To run a full end-to-end test with a real task:"
    echo "1. Initialize with: ./docker-init.sh"
    echo "2. Create a task: python scripts/enqueue_job.py <tenant_id> <user_id>"
    echo "3. Monitor: python scripts/monitor_task.py <task_id>"

    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please check the services and try again.${NC}"
    echo -e "${YELLOW}Debug tips:${NC}"
    echo "1. Check service logs: ./docker-logs.sh all"
    echo "2. Check service status: docker-compose ps"
    echo "3. Restart services: ./docker-stop.sh && ./docker-start.sh"
    exit 1
fi