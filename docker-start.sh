#!/bin/bash
#
# Start Docker services for XX Auto Jobs Applier
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}Starting XX Auto Jobs Applier Docker Services${NC}"
echo -e "${GREEN}===============================================${NC}\n"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}Created .env file. Please edit it with your actual values.${NC}"
        echo -e "${RED}Exiting. Please configure .env file first.${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example not found. Cannot proceed.${NC}"
        exit 1
    fi
fi

# Validate required environment variables
echo "Checking environment variables..."
source .env

required_vars=("DATABASE_URL" "REDIS_URL" "ENCRYPTION_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=($var)
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required environment variables:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    echo -e "${RED}Please configure them in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables validated${NC}\n"

# Build Docker images
echo "Building Docker images..."
docker-compose build --parallel

echo -e "${GREEN}✓ Docker images built${NC}\n"

# Start services
echo "Starting services..."

# Start database and redis first
docker-compose up -d postgres redis

echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}✓ PostgreSQL is ready${NC}"

echo "Waiting for Redis to be ready..."
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}✓ Redis is ready${NC}\n"

# Run database migrations
echo "Running database migrations..."
docker-compose exec -T postgres psql -U postgres -d autoapplyer < /dev/null || true

# Check if alembic is available
if [ -d "alembic" ]; then
    echo "Applying Alembic migrations..."
    docker run --rm \
        --network xx-autojobs_xx-network \
        -v "$PWD":/app \
        -w /app \
        -e DATABASE_URL="postgresql://postgres:postgres@postgres:5432/autoapplyer" \
        python:3.11-slim sh -c "pip install alembic psycopg2-binary && alembic upgrade head"
    echo -e "${GREEN}✓ Database migrations completed${NC}\n"
else
    echo -e "${YELLOW}Alembic migrations directory not found. Skipping migrations.${NC}\n"
fi

# Start API and workers
echo "Starting API and worker services..."
docker-compose up -d api worker-1 worker-2

# Optional: Start monitoring services if requested
if [ "$1" == "--with-monitoring" ]; then
    echo "Starting monitoring services (Grafana, Prometheus)..."
    docker-compose --profile monitoring up -d
fi

# Optional: Start nginx if requested
if [ "$1" == "--with-nginx" ] || [ "$2" == "--with-nginx" ]; then
    echo "Starting Nginx reverse proxy..."
    docker-compose up -d nginx
fi

echo -e "\n${GREEN}===============================================${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${GREEN}===============================================${NC}\n"

# Show service status
docker-compose ps

echo -e "\n${GREEN}Access points:${NC}"
echo "  API:        http://localhost:8000"
echo "  Metrics:    http://localhost:9090/metrics"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"

if [ "$1" == "--with-monitoring" ]; then
    echo "  Grafana:    http://localhost:3000 (admin/admin)"
    echo "  Prometheus: http://localhost:9091"
fi

if [ "$1" == "--with-nginx" ] || [ "$2" == "--with-nginx" ]; then
    echo "  Nginx:      http://localhost"
fi

echo -e "\n${GREEN}To view logs:${NC}"
echo "  docker-compose logs -f [service_name]"

echo -e "\n${GREEN}To stop all services:${NC}"
echo "  ./docker-stop.sh"