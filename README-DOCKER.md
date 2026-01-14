# Docker Setup Guide for XX Auto Jobs Applier

This guide provides comprehensive instructions for setting up and running XX Auto Jobs Applier using Docker.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Configuration](#configuration)
- [Management Scripts](#management-scripts)
- [Operations](#operations)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Prerequisites

- Docker Engine 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- 8GB RAM minimum (16GB recommended for multiple workers)
- 10GB free disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/XX/XX_Auto_Jobs_Applier.git
cd XX_Auto_Jobs_Applier
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env file with your values
nano .env
```

**Required environment variables:**
- `ENCRYPTION_KEY` - Generated encryption key
- `GEMINI_API_KEY` - Your Google Gemini API key
- `HH_LOGIN` - Your HH.ru login (will be encrypted)
- `HH_PASSWORD` - Your HH.ru password (will be encrypted)

### 3. Start Services

```bash
# Start all services
./docker-start.sh

# Or with monitoring (Grafana + Prometheus)
./docker-start.sh --with-monitoring

# Or with Nginx reverse proxy
./docker-start.sh --with-nginx
```

### 4. Initialize Database and Create User

```bash
# Run interactive initialization
./docker-init.sh

# This will:
# - Apply database migrations
# - Create a tenant and user
# - Load search configuration
```

### 5. Run a Job Search Task

```bash
# Enqueue a job search task
python scripts/enqueue_job.py <tenant_id> <user_id>

# Monitor task progress
python scripts/monitor_task.py <task_id> --watch

# View results
python scripts/view_applications.py <tenant_id> <user_id>
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Network                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Redis      │◄─────┤  FastAPI     │──────►│  PostgreSQL  │ │
│  │  (Queue)     │      │   (API)      │       │  (Database)  │ │
│  └──────────────┘      └──────────────┘       └──────────────┘ │
│         ▲                                              ▲        │
│         │                                              │        │
│  ┌──────┴──────────────────────────────────────────────┴─────┐ │
│  │              Worker Containers (2 instances)               │ │
│  │  ┌────────────────────────────────────────────────────┐   │ │
│  │  │        Browser Pool (5-10 Chromium instances)      │   │ │
│  │  └────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐                       │
│  │    Nginx     │      │   Grafana    │  (Optional)           │
│  │   (Proxy)    │      │ (Monitoring) │                       │
│  └──────────────┘      └──────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### Services

- **PostgreSQL**: Multi-tenant data storage
- **Redis**: FIFO task queue and result storage
- **API**: FastAPI service for monitoring and health checks
- **Workers**: Playwright-based automation workers (2 instances)
- **Nginx**: Reverse proxy (optional)
- **Grafana/Prometheus**: Monitoring stack (optional)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | postgresql://postgres:postgres@localhost:5432/autoapplyer |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `BROWSER_POOL_SIZE` | Number of browsers per worker | 5 |
| `BROWSER_HEADLESS` | Run browsers in headless mode | true |
| `WORKER_COUNT` | Number of worker instances | 2 |
| `ENCRYPTION_KEY` | Key for encrypting credentials | (must be generated) |
| `GEMINI_API_KEY` | Google Gemini API key | (required) |
| `HH_LOGIN` | HH.ru login | (required) |
| `HH_PASSWORD` | HH.ru password | (required) |

### Docker Compose Profiles

```bash
# Basic setup (default)
docker-compose up

# With monitoring
docker-compose --profile monitoring up

# Specific services
docker-compose up postgres redis api worker-1
```

## Management Scripts

### docker-start.sh
Starts all Docker services with health checks.

```bash
./docker-start.sh [options]
  --with-monitoring  # Include Grafana and Prometheus
  --with-nginx      # Include Nginx reverse proxy
```

### docker-stop.sh
Stops Docker services.

```bash
./docker-stop.sh [options]
  --clean      # Remove volumes (data will be lost)
  --clean-all  # Remove volumes, images, and containers
```

### docker-init.sh
Interactive initialization wizard for first-time setup.

```bash
./docker-init.sh
```

### docker-logs.sh
View service logs.

```bash
./docker-logs.sh [service] [lines]
  api       # View API logs
  worker-1  # View Worker 1 logs
  worker-2  # View Worker 2 logs
  all       # View all logs
  -f        # Follow logs in real-time
```

### docker-test.sh
Run automated tests to verify setup.

```bash
./docker-test.sh
```

## Operations

### Creating a Tenant and User

```bash
# Using CLI script
python scripts/manage_tenant.py create "Company Name" "company-slug"
python scripts/manage_user.py create <tenant_id> user@example.com \
    --name "John Doe" \
    --hh-login "login" \
    --hh-password "password"

# Or use interactive initialization
./docker-init.sh
```

### Loading Search Configuration

```bash
python scripts/load_search_config.py <tenant_id> <user_id> config.yaml
```

### Running Job Search Tasks

```bash
# Submit a task (returns task_id)
python scripts/enqueue_job.py <tenant_id> <user_id>

# Monitor task status
python scripts/monitor_task.py <task_id>

# Consume results from queue
python scripts/consume_results.py --mode completed

# View application history
python scripts/view_applications.py <tenant_id> <user_id>
```

### Database Migrations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Rollback migration
docker-compose exec api alembic downgrade -1
```

### Backup and Restore

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres autoapplyer > backup.sql

# Restore PostgreSQL
docker-compose exec -T postgres psql -U postgres autoapplyer < backup.sql

# Backup Redis
docker-compose exec redis redis-cli SAVE
docker cp xx-autojobs-redis:/data/dump.rdb ./redis-backup.rdb

# Restore Redis
docker cp ./redis-backup.rdb xx-autojobs-redis:/data/dump.rdb
docker-compose restart redis
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Queue statistics
curl http://localhost:8000/queue/stats

# Browser pool status
curl http://localhost:8000/pool/status

# Prometheus metrics
curl http://localhost:9090/metrics
```

### Grafana Dashboards

If monitoring is enabled:

1. Access Grafana: http://localhost:3000
2. Default credentials: admin/admin
3. Import provided dashboards from `grafana/dashboards/`

### Logging

Logs are stored in:
- `./logs/worker-1/` - Worker 1 logs
- `./logs/worker-2/` - Worker 2 logs
- Docker logs: `docker-compose logs [service]`

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

```bash
# Check service status
docker-compose ps

# View logs
./docker-logs.sh all

# Restart services
./docker-stop.sh && ./docker-start.sh
```

#### 2. Database Connection Issues

```bash
# Test database connection
docker-compose exec postgres pg_isready -U postgres

# Check migrations
docker-compose exec api alembic current
```

#### 3. Worker Not Processing Tasks

```bash
# Check Redis queue
docker-compose exec redis redis-cli LLEN tasks:pending

# View worker logs
./docker-logs.sh worker-1 -f

# Restart workers
docker-compose restart worker-1 worker-2
```

#### 4. Browser Automation Fails

```bash
# Check browser pool
curl http://localhost:8000/pool/status

# Increase shared memory
docker-compose down
# Edit docker-compose.yml, increase shm_size
docker-compose up -d
```

#### 5. Out of Memory

```bash
# Check resource usage
docker stats

# Adjust resource limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

### Debug Mode

Enable debug logging:

```bash
# Edit .env
DEBUG=true
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

## Security Considerations

### Best Practices

1. **Environment Variables**
   - Never commit `.env` file to version control
   - Use strong encryption keys (generated, not manual)
   - Rotate credentials regularly

2. **Network Security**
   - Use internal Docker networks
   - Expose only necessary ports
   - Enable firewall rules

3. **Database Security**
   - Change default PostgreSQL password
   - Use SSL for database connections in production
   - Regular backups

4. **API Security**
   - Implement authentication for API endpoints
   - Use HTTPS in production (configure Nginx)
   - Rate limiting enabled by default

5. **Container Security**
   - Run containers as non-root users
   - Keep base images updated
   - Scan images for vulnerabilities

### Production Deployment

For production environments:

1. Use Docker Swarm or Kubernetes
2. Implement secrets management (Vault, K8s secrets)
3. Set up monitoring and alerting
4. Configure log aggregation (ELK stack)
5. Implement backup strategy
6. Use container registry for images
7. Set up CI/CD pipeline

## Performance Tuning

### PostgreSQL

```sql
-- Adjust in docker-compose.yml environment
POSTGRES_MAX_CONNECTIONS=200
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
```

### Redis

```bash
# Edit redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Workers

```yaml
# Adjust in docker-compose.yml
BROWSER_POOL_SIZE: 10  # More browsers
WORKER_COUNT: 4         # More workers
```

## Support

For issues and questions:
- Check logs: `./docker-logs.sh all`
- Run tests: `./docker-test.sh`
- Review documentation in `scrapper.md`
- Submit issues on GitHub

## License

[Your License Here]

---

**Version:** 2.0.0
**Last Updated:** January 2024
**Status:** Production Ready