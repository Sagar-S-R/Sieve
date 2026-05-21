# Deployment Checklist - Task Management Commands

## ✅ Pre-Deployment Checklist

### 1. Environment Variables
- [ ] `.env` file exists with all required variables
- [ ] `TELEGRAM_BOT_TOKEN` is set
- [ ] `GROQ_API_KEY` is set (for deadline parsing)
- [ ] `DATABASE_URL` is correct (port 5433)
- [ ] `RABBITMQ_URL` is correct
- [ ] `REDIS_URL` is correct

### 2. Code Changes
- [x] Database indexes added to `init.sql`
- [x] API Gateway config includes `GROQ_API_KEY`
- [x] All command handlers implemented
- [x] Group update detection implemented
- [x] LLM deadline parsing implemented
- [x] Cache invalidation implemented

### 3. Docker Setup
- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space for volumes
- [ ] Ports available: 8000 (API), 5433 (Postgres), 6379 (Redis), 5672 (RabbitMQ)

---

## 🚀 Deployment Steps

### Step 1: Stop Existing Services
```bash
cd /path/to/Sieve
docker-compose down
```

### Step 2: Remove Database Volume (IMPORTANT!)
This will recreate the database with new indexes.

**⚠️ WARNING: This will delete all existing data!**

```bash
docker volume rm sieve_postgres_data
```

If you want to keep data, manually add indexes instead:
```bash
docker exec -it sieve_postgres psql -U user -d sieve

-- Run these commands:
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_group_title ON tasks(group_id, LOWER(title));
\q
```

### Step 3: Rebuild Images
```bash
docker-compose build api_gateway text_extractor
```

### Step 4: Start Services
```bash
docker-compose up -d
```

### Step 5: Verify Services Started
```bash
docker-compose ps
```

All services should show "Up" status.

### Step 6: Check Logs
```bash
# API Gateway logs
docker logs sieve_api_gateway -f

# Text Extractor logs
docker logs sieve_text_extractor -f

# Look for:
# - "Connected to RabbitMQ"
# - "Prometheus metrics exposed"
# - No error messages
```

### Step 7: Verify Database Indexes
```bash
docker exec -it sieve_postgres psql -U user -d sieve -c "\d tasks"
```

Should show:
- `idx_tasks_user_id`
- `idx_tasks_group_title`

---

## 🧪 Testing After Deployment

### Test 1: Private Chat Commands

**Open Telegram and message your bot privately:**

```
1. Send: /start
   Expected: Welcome message with "Add to Group" button

2. Send: /help
   Expected: Help message with all commands listed

3. Send: /tasks
   Expected: "No tasks found" (if no tasks exist)

4. Send: /delete 999
   Expected: "Task not found or you don't have permission"

5. Send: /edit 999
   Expected: "Task not found or you don't have permission"

6. Send: /delete abc
   Expected: "Invalid task ID. Must be a number."
```

### Test 2: Group Chat - Task Creation

**In a group where bot is added:**

```
1. Post: "Submit assignment by tomorrow 5pm"
   Expected: Bot processes message (check logs)

2. Send /tasks in private chat
   Expected: Task appears in your list

3. Send /delete <task_id> in private chat
   Expected: Task deleted successfully
```

### Test 3: Group Chat - Corrections

**In the same group:**

```
1. Post: "Submit report by May 25"
   Expected: Task created

2. Post: "Sorry, report deadline is May 30"
   Expected: Bot sends confirmation "✅ Updated deadline for..."

3. Send /tasks in private chat
   Expected: Task shows May 30 deadline
```

### Test 4: Edit Command Flow

**In private chat:**

```
1. Create a task in group first
2. Send: /tasks (note the task ID)
3. Send: /edit <task_id>
   Expected: Bot asks for new deadline
4. Reply: "tomorrow 5pm"
   Expected: "✅ Task updated successfully!"
5. Send: /tasks
   Expected: Task shows new deadline
```

---

## 🐛 Troubleshooting

### Issue: "GROQ_API_KEY not found"
**Solution:** Add `GROQ_API_KEY` to your `.env` file and restart:
```bash
docker-compose restart api_gateway
```

### Issue: Commands not responding
**Solution:** Check API Gateway logs:
```bash
docker logs sieve_api_gateway -f
```
Look for errors in webhook processing.

### Issue: Group updates not working
**Solution:** Check Text Extractor logs:
```bash
docker logs sieve_text_extractor -f
```
Look for "[UPDATE]" or "[CONTEXT]" log messages.

### Issue: "Task not found" for valid task
**Solution:** Check database:
```bash
docker exec -it sieve_postgres psql -U user -d sieve -c "SELECT * FROM tasks LIMIT 5;"
```

### Issue: Deadline parsing fails
**Solution:** Check if GROQ_API_KEY is valid and has quota:
```bash
docker logs sieve_api_gateway | grep "LLM"
```

### Issue: Redis connection errors
**Solution:** Restart Redis:
```bash
docker-compose restart redis
```

---

## 📊 Monitoring

### Check Service Health
```bash
# All services status
docker-compose ps

# Resource usage
docker stats

# Disk usage
docker system df
```

### Check Logs for Errors
```bash
# API Gateway
docker logs sieve_api_gateway --tail 100 | grep ERROR

# Text Extractor
docker logs sieve_text_extractor --tail 100 | grep ERROR

# RabbitMQ
docker logs sieve_rabbitmq --tail 100 | grep ERROR
```

### Check Database
```bash
# Connect to database
docker exec -it sieve_postgres psql -U user -d sieve

# Check task count
SELECT COUNT(*) FROM tasks;

# Check recent tasks
SELECT id, user_id, title, deadline FROM tasks ORDER BY created_at DESC LIMIT 10;

# Check indexes
\d tasks

# Exit
\q
```

### Check Redis Cache
```bash
# Connect to Redis
docker exec -it sieve_redis redis-cli

# Check cache keys
KEYS cache:*

# Check edit states
KEYS edit_task:*

# Exit
exit
```

---

## 🔄 Rollback Plan

If something goes wrong:

### Option 1: Restart Services
```bash
docker-compose restart
```

### Option 2: Rebuild from Previous Version
```bash
git checkout <previous-commit>
docker-compose down
docker-compose build
docker-compose up -d
```

### Option 3: Restore Database Backup
```bash
# If you have a backup
docker exec -i sieve_postgres psql -U user -d sieve < backup.sql
```

---

## ✅ Post-Deployment Verification

### Checklist
- [ ] All services running (`docker-compose ps`)
- [ ] No errors in logs
- [ ] Database indexes created
- [ ] `/start` command works
- [ ] `/help` command works
- [ ] `/tasks` command works
- [ ] `/delete` command works
- [ ] `/edit` command works
- [ ] Group task creation works
- [ ] Group corrections work
- [ ] Cache invalidation works
- [ ] Prometheus metrics accessible (http://localhost:8001/metrics)

---

## 📝 Notes

### Database Indexes
The new indexes improve query performance:
- `idx_tasks_user_id` - Speeds up `/tasks` command
- `idx_tasks_group_title` - Speeds up group update detection

### Redis State
Edit states are stored with 5-minute TTL:
- Key: `edit_task:{user_id}`
- Auto-expires after 5 minutes
- Prevents memory leaks

### Cache Invalidation
Cache is invalidated on:
- Task deletion
- Task update (edit)
- Group bulk update

### LLM Usage
Deadline parsing uses Groq API:
- Model: llama-3.1-70b-versatile
- Temperature: 0.1
- Max tokens: 500
- Cost: ~$0.0001 per request

---

## 🎉 Success Criteria

Deployment is successful when:
1. ✅ All services are running
2. ✅ No errors in logs
3. ✅ All commands respond correctly
4. ✅ Group updates work
5. ✅ Cache is working (check logs for "CACHE HIT")
6. ✅ Database indexes exist

---

## 📞 Support

If you encounter issues:
1. Check logs first
2. Verify environment variables
3. Check database connectivity
4. Verify Redis connectivity
5. Check RabbitMQ queue status

**Logs Location:**
- API Gateway: `docker logs sieve_api_gateway`
- Text Extractor: `docker logs sieve_text_extractor`
- Database: `docker logs sieve_postgres`
- Redis: `docker logs sieve_redis`
- RabbitMQ: `docker logs sieve_rabbitmq`
