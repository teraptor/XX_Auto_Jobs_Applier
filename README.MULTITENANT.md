# Multi-Tenant Auto Jobs Applier

Multi-tenant version of the XX Auto Jobs Applier with PostgreSQL, Redis FIFO queues, and shared browser pool.

## Architecture

- **PostgreSQL**: Multi-tenant data storage with tenant_id isolation
- **Redis FIFO**: Task input queue and result output queues with ID tracking
- **Shared Browser Pool**: 5-10 Playwright browsers reused across tenants
- **Worker**: Processes tasks from Redis queue with Playwright automation
- **Minimal API**: FastAPI for monitoring and health checks only

## Features

- ✅ Multi-tenant isolation (shared schema + tenant_id)
- ✅ Redis FIFO queues for tasks and results
- ✅ ID tracking: task_id (input) ↔ result_id (output)
- ✅ Shared browser pool for efficiency
- ✅ Encrypted HH.ru credentials storage
- ✅ LLM response caching
- ✅ Browser session persistence
- ✅ CLI tools for management
- ✅ Docker containerization
- ✅ Repository pattern for data access

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add the key to .env
echo "ENCRYPTION_KEY=<your-key-here>" >> .env
```

### 3. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose -f docker-compose-dev.yml up -d postgres redis

# Wait for services to be healthy
docker-compose -f docker-compose-dev.yml ps

# Run database migrations
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/autoapplyer"
python -m alembic upgrade head
```

### 4. Create Tenant and User

```bash
# Create tenant
python scripts/manage_tenant.py create "Company A" company-a

# Output:
# ✅ Tenant created successfully!
#    ID: <tenant-id>
#    Name: Company A
#    Slug: company-a
#    Status: active

# Create user
python scripts/manage_user.py create <tenant-id> "user@example.com" "hh_login" "hh_password"

# Output:
# ✅ User created successfully!
#    ID: <user-id>
#    Email: user@example.com
#    HH Login: hh_login
#    Active: True
```

### 5. Load Search Configuration

```bash
# Load search config from YAML
python scripts/load_search_config.py load <tenant-id> <user-id> data_folder/search_config.yaml "Python Developer"

# Output:
# ✅ Search config loaded successfully!
#    ID: <config-id>
#    Name: Python Developer
#    Active: True
```

### 6. Enqueue Job Task

```bash
# Enqueue task to Redis FIFO
python scripts/enqueue_job.py <tenant-id> <user-id>

# Output:
# ✅ Task enqueued successfully!
#    Task ID: <task-id>
#    Position in queue: 1
```

### 7. Start Worker

```bash
# Start worker (in separate terminal)
docker-compose -f docker-compose-dev.yml up worker

# Or run locally:
export REDIS_URL="redis://localhost:6379/0"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/autoapplyer"
export ENCRYPTION_KEY="<your-key>"
export BROWSER_POOL_SIZE=5
export HEADLESS=true

python -m src.worker.task_worker
```

### 8. Monitor Task

```bash
# Monitor task status
python scripts/monitor_task.py <task-id>

# Watch mode (auto-refresh)
python scripts/monitor_task.py <task-id> --watch

# Output:
# Task ID: <task-id>
# Status: processing
# Enqueued: 2024-01-15 10:30:00
# Processing: 2024-01-15 10:30:05
```

### 9. Consume Results

```bash
# Consume results from FIFO queue
python scripts/consume_results.py --mode completed --timeout 60

# Output:
# ✅ Result from task <task-id>:
# {
#   "task_id": "<task-id>",
#   "result_id": "<result-id>",
#   "applications_processed": 10,
#   "applications_success": 8,
#   "applications_failed": 2
# }
```

### 10. View Applications

```bash
# List all applications
python scripts/view_applications.py list <tenant-id> <user-id>

# Filter by status
python scripts/view_applications.py list <tenant-id> <user-id> --status success

# Show statistics
python scripts/view_applications.py stats <tenant-id> <user-id>

# Output:
# Application Statistics for user@example.com:
#   Total Applications: 50
#   ✅ Success: 42
#   ❌ Failed: 5
#   ⏭️  Skipped: 3
#
#   Success Rate: 84.0%
```

## CLI Tools

### Tenant Management

```bash
# Create tenant
python scripts/manage_tenant.py create "Company A" company-a

# List tenants
python scripts/manage_tenant.py list
python scripts/manage_tenant.py list --status active

# Get tenant details
python scripts/manage_tenant.py get company-a

# Suspend tenant
python scripts/manage_tenant.py suspend <tenant-id>

# Activate tenant
python scripts/manage_tenant.py activate <tenant-id>
```

### User Management

```bash
# Create user
python scripts/manage_user.py create <tenant-id> "user@example.com" "hh_login" "hh_password"

# List users
python scripts/manage_user.py list <tenant-id>
python scripts/manage_user.py list <tenant-id> --active

# Get user details
python scripts/manage_user.py get <tenant-id> <user-id>

# Deactivate user
python scripts/manage_user.py deactivate <tenant-id> <user-id>

# Activate user
python scripts/manage_user.py activate <tenant-id> <user-id>
```

### Search Config Management

```bash
# Load config from YAML
python scripts/load_search_config.py load <tenant-id> <user-id> config.yaml "Config Name"

# Load without activating
python scripts/load_search_config.py load <tenant-id> <user-id> config.yaml "Config Name" --no-activate

# List configs
python scripts/load_search_config.py list <tenant-id> <user-id>

# Show active config
python scripts/load_search_config.py active <tenant-id> <user-id>

# Set config as active
python scripts/load_search_config.py set-active <tenant-id> <user-id> <config-id>
```

### Application Viewing

```bash
# List applications
python scripts/view_applications.py list <tenant-id> <user-id>
python scripts/view_applications.py list <tenant-id> <user-id> --status success
python scripts/view_applications.py list <tenant-id> <user-id> --limit 100

# Show statistics
python scripts/view_applications.py stats <tenant-id> <user-id>

# Find by task_id
python scripts/view_applications.py task <tenant-id> <task-id>
```

## API Endpoints

The minimal API provides monitoring endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Queue statistics
curl http://localhost:8000/queue/stats

# Task status
curl http://localhost:8000/task/<task-id>/status

# Result data
curl http://localhost:8000/result/<result-id>

# Reverse lookup (result_id → task_id)
curl http://localhost:8000/result/<result-id>/task

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Redis Queue Architecture

### Task FIFO Queue

```
tasks:pending (LIST)
├── LPUSH: Enqueue new task with task_id
└── BRPOP: Dequeue oldest task (FIFO)

Metadata (TTL 24h):
├── task:<task_id>:status → "pending|processing|completed|failed"
├── task:<task_id>:data → JSON task data
├── task:<task_id>:result_id → UUID (when completed)
```

### Result FIFO Queues

```
results:completed (LIST)
├── LPUSH: Publish success result with result_id
└── BRPOP: Consume oldest result (FIFO)

results:failed (LIST)
├── LPUSH: Publish failure result with result_id
└── BRPOP: Consume oldest result (FIFO)

Metadata (TTL 24h):
├── result:<result_id>:data → JSON result data
├── result:<result_id>:task_id → UUID (reverse lookup)
```

### ID Tracking Flow

```
1. Client → Enqueue task → Get task_id
2. Client → Monitor task_id → Check status
3. Worker → Process task → Update status
4. Worker → Publish result → Get result_id
5. Client → Consume result → Get result_id
6. Client → Query result_id → Get task_id (reverse lookup)
```

## Database Schema

### Multi-Tenant Tables

- **tenants**: Tenant isolation and status management
- **users**: User accounts with encrypted HH.ru credentials
- **applications**: Job application history with task_id tracking
- **search_configs**: JSONB search configurations
- **browser_sessions**: Playwright session state (cookies, localStorage)
- **llm_cache**: LLM response caching with prompt hashing
- **job_tasks**: Long-term task history (supplements Redis TTL 24h)

### Tenant Isolation

All tables (except `tenants`) include:
- `tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE`
- Indexes: `idx_<table>_tenant_user ON <table>(tenant_id, user_id)`

### ID Tracking

```sql
-- applications table
task_id UUID  -- From Redis tasks:pending

-- job_tasks table
task_id UUID UNIQUE NOT NULL    -- From Redis tasks:pending
result_id UUID                  -- From Redis results:completed/failed
```

## Shared Browser Pool

The worker manages 5-10 Playwright browsers reused across tenants:

```python
from src.browser import BrowserPool, BrowserSession

# Initialize pool
async with BrowserPool(pool_size=5) as pool:
    # Acquire browser
    async with BrowserSession(pool, tenant_id, user_id) as browser:
        # Use browser
        context = await browser.browser.new_context()
        page = await context.new_page()
        # ...
    # Browser automatically released back to pool
```

### Pool Benefits

- **Resource Efficiency**: Reuse browsers instead of creating/destroying
- **Startup Time**: Browsers pre-launched and ready
- **Memory**: Fixed pool size prevents memory exhaustion
- **Concurrency**: Multiple tenants share pool fairly

## Storage Adapter

The storage adapter provides database-backed interface compatible with existing YAML code:

```python
from src.storage import StorageAdapter, TenantContext

# Create context
context = TenantContext(tenant_id="...", user_id="...")

# Initialize adapter
storage = StorageAdapter(db_pool, context)

# Use like YAML (but backed by PostgreSQL)
search_config = await storage.get_search_config()  # Replaces load_yaml_file()
await storage.save_application(...)  # Replaces writing to YAML
already_applied = await storage.is_already_applied(vacancy_id)
```

## Credentials Management

HH.ru credentials are encrypted using Fernet (symmetric encryption):

```python
from src.storage import CredentialsManager

# Initialize manager
creds = CredentialsManager(user_repo, context)

# Get credentials (auto-decrypted)
hh_login, hh_password = await creds.get_hh_credentials()

# Update credentials (auto-encrypted)
await creds.update_hh_credentials("new_login", "new_password")
```

## Development

### Run Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# Create new migration
alembic revision -m "description"
```

### Run Tests

```bash
pytest tests/
```

### Local Development

```bash
# Install dependencies
pip install -r requirements-multitenant.txt

# Run worker locally
python -m src.worker.task_worker

# Run API locally
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Production Deployment

### Docker Compose

```bash
# Production stack
docker-compose -f docker-compose-prod.yml up -d

# Scale workers
docker-compose -f docker-compose-prod.yml up -d --scale worker=3
```

### Environment Variables

Required for production:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ENCRYPTION_KEY`: Fernet encryption key
- `BROWSER_POOL_SIZE`: Number of browsers per worker
- `HEADLESS`: true for production

### Resource Requirements

Per worker:
- **CPU**: 2-4 cores
- **RAM**: 4-8 GB (with BROWSER_POOL_SIZE=5)
- **Disk**: 1 GB for Playwright browsers

## Monitoring

### Prometheus Metrics

```
# Task processing metrics
task_worker_tasks_processed_total
task_worker_tasks_succeeded_total
task_worker_tasks_failed_total
task_worker_processing_duration_seconds

# Browser pool metrics
browser_pool_size
browser_pool_in_use
browser_pool_available

# Queue metrics
redis_queue_pending_tasks
redis_queue_completed_results
redis_queue_failed_results
```

### Logging

All components use structured logging:
- Worker: Task processing logs
- Browser Pool: Acquisition/release logs
- Storage: Database operation logs
- API: HTTP request logs

## Troubleshooting

### Worker not processing tasks

```bash
# Check worker logs
docker-compose logs -f worker

# Check Redis connection
redis-cli -h localhost -p 6379 ping

# Check queue length
redis-cli -h localhost -p 6379 LLEN tasks:pending
```

### Database connection issues

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check migrations
alembic current
```

### Browser issues

```bash
# Check browser pool stats
curl http://localhost:8000/browser/stats

# Restart worker to reset pool
docker-compose restart worker
```

### Task stuck in processing

```bash
# Check task status
python scripts/monitor_task.py <task-id>

# View worker logs
docker-compose logs -f worker | grep <task-id>
```

## License

Same as original XX_Auto_Jobs_Applier project.
