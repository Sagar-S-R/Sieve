# Docker Guide for Sieve

## Why Docker?

### The Problem Docker Solves

**Before Docker:**
- "Works on my machine" syndrome
- Complex dependency management
- Environment inconsistencies
- Difficult deployment process
- Hard to scale

**With Docker:**
- ✅ Consistent environments (dev = staging = prod)
- ✅ Isolated dependencies (no conflicts)
- ✅ Easy deployment (ship the container)
- ✅ Reproducible builds
- ✅ Efficient resource usage

---

## Why Docker for Sieve?

### 1. **Microservices Architecture**

Sieve has 5 independent services:
- `api_gateway` - Handles Telegram webhooks
- `text_extractor` - Processes text messages with LLM
- `media_extractor` - Processes images/documents
- `cron_notifier` - Sends scheduled reminders
- Infrastructure (PostgreSQL, Redis, RabbitMQ)

**Docker Benefits:**
- Each service runs in isolated container
- Independent scaling (scale text_extractor without affecting others)
- Independent deployment (update one service without downtime)
- Clear service boundaries

### 2. **Dependency Isolation**

Each service has different dependencies:
- `text_extractor`: Groq SDK, LangGraph, asyncpg
- `media_extractor`: Google Vision API, PIL
- `api_gateway`: FastAPI, httpx

**Docker Benefits:**
- No dependency conflicts
- Each container has its own Python environment
- Easy to upgrade one service's dependencies

### 3. **Development Consistency**

**Problem:** Developer A uses Python 3.11, Developer B uses 3.12
**Solution:** Docker ensures everyone uses same Python version

### 4. **Easy Onboarding**

**Without Docker:**
```bash
# Install Python 3.11
# Install PostgreSQL
# Install Redis
# Install RabbitMQ
# Set up virtual environments
# Install dependencies for each service
# Configure environment variables
# Start each service manually
```

**With Docker:**
```bash
docker-compose up
# Done! Everything running in 30 seconds
```

---

## Docker Architecture for Sieve

### Container Structure

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ api_gateway  │  │text_extractor│  │media_extractor│ │
│  │   :8000      │  │   :8001      │  │              │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│  ┌──────────────┐  ┌──────┴───────┐  ┌──────────────┐ │
│  │  PostgreSQL  │  │   RabbitMQ   │  │    Redis     │ │
│  │   :5432      │  │   :5672      │  │   :6379      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │  Prometheus  │  │   Grafana    │                    │
│  │   :9090      │  │   :3000      │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### Volume Persistence

**Why Volumes?**
- Containers are ephemeral (data lost on restart)
- Volumes persist data outside containers

**Sieve Volumes:**
```yaml
volumes:
  postgres_data:     # Database data
  prometheus_data:   # Metrics history
  grafana_data:      # Dashboards & settings
```

---

## Docker Commands Reference

### Basic Commands

#### 1. Start All Services
```bash
docker-compose up
```
**What it does:**
- Builds images if needed
- Creates containers
- Starts all services
- Shows logs in terminal

**Options:**
```bash
docker-compose up -d              # Detached mode (background)
docker-compose up --build         # Force rebuild images
docker-compose up api_gateway     # Start only one service
```

---

#### 2. Stop All Services
```bash
docker-compose down
```
**What it does:**
- Stops all containers
- Removes containers
- Removes networks
- **Keeps volumes** (data preserved)

**Options:**
```bash
docker-compose down -v            # Remove volumes too (deletes data!)
docker-compose down --rmi all     # Remove images too
```

---

#### 3. View Logs
```bash
docker-compose logs
```
**What it does:**
- Shows logs from all services

**Options:**
```bash
docker-compose logs -f                    # Follow logs (live)
docker-compose logs api_gateway           # Logs from one service
docker-compose logs --tail 50             # Last 50 lines
docker-compose logs -f text_extractor     # Follow one service
```

---

#### 4. Rebuild Services
```bash
docker-compose up -d --build
```
**When to use:**
- After code changes
- After dependency changes (requirements.txt)
- After Dockerfile changes

**Specific service:**
```bash
docker-compose up -d --build text_extractor
```

---

#### 5. Restart Services
```bash
docker-compose restart
```
**What it does:**
- Restarts containers without rebuilding

**Specific service:**
```bash
docker-compose restart api_gateway
```

---

#### 6. View Running Containers
```bash
docker-compose ps
```
**Output:**
```
NAME                   STATUS    PORTS
sieve_api_gateway      Up        0.0.0.0:8000->8000/tcp
sieve_text_extractor   Up        0.0.0.0:8001->8001/tcp
sieve_postgres         Up        0.0.0.0:5433->5432/tcp
sieve_redis            Up        0.0.0.0:6379->6379/tcp
sieve_rabbitmq         Up        0.0.0.0:5672->5672/tcp
```

---

#### 7. Execute Commands in Container
```bash
docker-compose exec <service> <command>
```

**Examples:**
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U user -d sieve

# Access Redis CLI
docker-compose exec redis redis-cli

# Access Python shell in text_extractor
docker-compose exec text_extractor python

# Run bash in container
docker-compose exec api_gateway bash
```

---

#### 8. View Container Stats
```bash
docker stats
```
**Shows:**
- CPU usage
- Memory usage
- Network I/O
- Disk I/O

---

### Advanced Commands

#### 9. Scale Services
```bash
docker-compose up -d --scale text_extractor=3
```
**What it does:**
- Runs 3 instances of text_extractor
- Load balanced by RabbitMQ

---

#### 10. View Networks
```bash
docker network ls
docker network inspect sieve_default
```

---

#### 11. View Volumes
```bash
docker volume ls
docker volume inspect sieve_postgres_data
```

---

#### 12. Clean Up Everything
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove everything (DANGEROUS!)
docker system prune -a --volumes
```

---

## Development Workflow

### 1. First Time Setup
```bash
# Clone repo
git clone <repo-url>
cd sieve

# Create .env file
cp .env.example .env
# Edit .env with your tokens

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

### 2. Making Code Changes

**Workflow:**
```bash
# 1. Make changes to code
vim workers/text_extractor/nodes/extractor_node.py

# 2. Rebuild affected service
docker-compose up -d --build text_extractor

# 3. Check logs
docker-compose logs -f text_extractor

# 4. Test changes
# Send message to bot
```

---

### 3. Debugging

**Check if services are running:**
```bash
docker-compose ps
```

**View logs for errors:**
```bash
docker-compose logs text_extractor | grep ERROR
```

**Access container shell:**
```bash
docker-compose exec text_extractor bash
```

**Check environment variables:**
```bash
docker-compose exec text_extractor env
```

**Test database connection:**
```bash
docker-compose exec postgres psql -U user -d sieve -c "SELECT COUNT(*) FROM tasks;"
```

---

### 4. Database Operations

**Access PostgreSQL:**
```bash
docker-compose exec postgres psql -U user -d sieve
```

**Run SQL queries:**
```sql
-- View all tasks
SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10;

-- View subscribers
SELECT * FROM group_subscriptions;

-- Count tasks by group
SELECT group_id, COUNT(*) FROM tasks GROUP BY group_id;
```

**Backup database:**
```bash
docker-compose exec postgres pg_dump -U user sieve > backup.sql
```

**Restore database:**
```bash
cat backup.sql | docker-compose exec -T postgres psql -U user sieve
```

---

### 5. Redis Operations

**Access Redis CLI:**
```bash
docker-compose exec redis redis-cli
```

**Redis commands:**
```bash
# View all keys
KEYS *

# Get HITL lock
GET awaiting_clarification:123456

# Check message processed
EXISTS processed:-1001234567890:12345

# View all HITL locks
KEYS awaiting_clarification:*

# Clear all caches (DANGEROUS!)
FLUSHALL
```

---

### 6. RabbitMQ Operations

**Access Management UI:**
```
http://localhost:15672
Username: guest
Password: guest
```

**View queues:**
- fast_text_queue
- heavy_media_queue

**Purge queue (clear all messages):**
- Go to Queues tab
- Click queue name
- Click "Purge Messages"

---

## Troubleshooting

### Problem: Container won't start

**Check logs:**
```bash
docker-compose logs <service>
```

**Common issues:**
- Port already in use
- Missing environment variables
- Database not ready (wait for healthcheck)

---

### Problem: "Port already in use"

**Find process using port:**
```bash
# Windows
netstat -ano | findstr :8000

# Kill process
taskkill /PID <pid> /F
```

**Or change port in docker-compose.yml:**
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

---

### Problem: Database connection failed

**Check if PostgreSQL is running:**
```bash
docker-compose ps postgres
```

**Check healthcheck:**
```bash
docker inspect sieve_postgres | grep Health
```

**Restart PostgreSQL:**
```bash
docker-compose restart postgres
```

---

### Problem: Out of disk space

**Check disk usage:**
```bash
docker system df
```

**Clean up:**
```bash
docker system prune -a
```

---

### Problem: Changes not reflected

**Rebuild image:**
```bash
docker-compose up -d --build <service>
```

**Clear Docker cache:**
```bash
docker-compose build --no-cache <service>
```

---

## Performance Tips

### 1. Use BuildKit
```bash
# Add to .env or shell profile
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
```

### 2. Multi-stage Builds
Already implemented in Dockerfiles:
```dockerfile
# Build stage
FROM python:3.11-slim as builder
# Install dependencies

# Runtime stage
FROM python:3.11-slim
# Copy only what's needed
```

### 3. Layer Caching
Order matters in Dockerfile:
```dockerfile
# ✅ Good (dependencies cached)
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# ❌ Bad (cache invalidated on every code change)
COPY . .
RUN pip install -r requirements.txt
```

---

## Production Considerations

### 1. Resource Limits
Add to docker-compose.yml:
```yaml
services:
  text_extractor:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 2. Health Checks
Already implemented:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U user -d sieve"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### 3. Restart Policies
Already set:
```yaml
restart: unless-stopped
```

### 4. Logging
Configure log rotation:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## Docker vs Kubernetes

| Feature | Docker Compose | Kubernetes |
|---------|---------------|------------|
| **Use Case** | Development, small deployments | Production, large scale |
| **Complexity** | Simple | Complex |
| **Scaling** | Manual | Automatic |
| **High Availability** | No | Yes |
| **Load Balancing** | Basic | Advanced |
| **Self-healing** | Restart only | Full orchestration |
| **Multi-host** | No | Yes |

**When to use Docker Compose:**
- Development environment ✅
- Single server deployment ✅
- Quick prototyping ✅

**When to use Kubernetes:**
- Production at scale
- Multi-region deployment
- Auto-scaling needed
- High availability required

---

## Summary

**Docker gives us:**
1. ✅ Consistent environments
2. ✅ Easy setup (one command)
3. ✅ Isolated services
4. ✅ Simple deployment
5. ✅ Reproducible builds

**Key Commands:**
```bash
docker-compose up -d              # Start
docker-compose down               # Stop
docker-compose logs -f            # View logs
docker-compose up -d --build      # Rebuild
docker-compose restart            # Restart
docker-compose ps                 # Status
```

**Next Step:** See `KUBERNETES.md` for production deployment

---

Last Updated: 2026-05-11
