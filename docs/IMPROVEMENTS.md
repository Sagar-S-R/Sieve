# System Improvements Roadmap

This document tracks all planned improvements for the Sieve reminder bot system.

## Status Legend
- ✅ Implemented
- 🚧 In Progress
- ⏳ Planned
- ❌ Blocked

---

## 🔴 CRITICAL PRIORITY

### 1. Webhook Security - Telegram Signature Verification
**Status:** ✅ Implemented (Optional Mode)
**Effort:** Low (1 day)
**Impact:** Critical

**Problem:** Anyone can POST to `/webhook` endpoint and inject fake messages

**Solution:** Verify `X-Telegram-Bot-Api-Secret-Token` header on all webhook requests

**Files modified:**
- `api_gateway/routers/webhook.py`

**Implementation:**
```python
def verify_telegram_webhook(request: Request, bot_token: str):
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret_token:
        return  # Skip verification for backward compatibility
    if not hmac.compare_digest(secret_token, bot_token):
        raise HTTPException(status_code=403, detail="Invalid Telegram signature")
```

**Note:** Currently optional (skips if no header present). For production, set secret token when configuring webhook.

---

### 2. Database Transactions for Multi-Task Creation
**Status:** ✅ Implemented
**Effort:** Low (1 day)
**Impact:** High

**Problem:** If task creation fails halfway through subscriber loop, partial data is saved

**Solution:** Wrap multi-task creation in atomic database transaction

**Files modified:**
- `workers/text_extractor/main.py`
- `workers/text_extractor/services/database.py`

**Implementation:**
```python
async def save_tasks_atomic(subscribers, group_id, message_sender_id, title, action_required, deadline):
    async with conn.transaction():
        for subscriber_id in subscribers:
            task_id = await conn.fetchval(INSERT_QUERY, ...)
            task_ids.append(task_id)
    return task_ids
```

**Result:** All tasks created or none (atomic operation)

---

### 3. Message Deduplication (Idempotency)
**Status:** ✅ Implemented
**Effort:** Medium (2 days)
**Impact:** High

**Problem:** If Telegram webhook retries, same message gets processed twice

**Solution:** Track processed message IDs in Redis with TTL

**Files modified:**
- `workers/text_extractor/main.py`
- `workers/text_extractor/services/redis_client.py`

**Implementation:**
```python
def is_message_processed(message_id, group_id):
    key = f"processed:{group_id}:{message_id}"
    return redis_client.exists(key)

def mark_message_processed(message_id, group_id, ttl=3600):
    key = f"processed:{group_id}:{message_id}"
    redis_client.setex(key, ttl, "1")
```

**Flow:**
1. Message arrives → Check if processed
2. If yes → Skip and ACK
3. If no → Mark as processed immediately (prevent race conditions)
4. Process message
5. TTL expires after 1 hour

---

### 4. Timezone Conversion in Code (Not LLM)
**Status:** ✅ Implemented
**Effort:** Low (1 day)
**Impact:** High

**Problem:** LLM can miscalculate IST to UTC conversion (5.5 hour offset)

**Solution:** Do timezone conversion in Python after LLM extraction

**Files modified:**
- `workers/text_extractor/core/timezone_utils.py` (new file)
- `workers/text_extractor/nodes/extractor_node.py`
- `workers/text_extractor/nodes/hitl_merge_node.py`

**Implementation:**
```python
from datetime import timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
UTC_TZ = timezone.utc

def convert_ist_to_utc(ist_datetime_str: str) -> str:
    ist_dt = datetime.fromisoformat(ist_datetime_str)
    if ist_dt.tzinfo is None:
        ist_dt = ist_dt.replace(tzinfo=IST_TZ)
    utc_dt = ist_dt.astimezone(UTC_TZ)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
```

**Flow:**
1. LLM extracts deadline in IST (e.g., "2026-05-12T18:00:00")
2. Python converts IST → UTC (e.g., "2026-05-12T12:30:00Z")
3. Store UTC in database
4. Cron job compares UTC times

---

### 4.1. EOD (End of Day) Time Interpretation
**Status:** ✅ Implemented
**Effort:** Low (1 hour)
**Impact:** High

**Problem:** LLM interpreted "EOD" as 12:00:00 (noon) instead of 23:59:59 (11:59 PM)

**Solution:** Added explicit TIME INTERPRETATION RULES to LLM prompts

**Files modified:**
- `workers/text_extractor/nodes/extractor_node.py`
- `workers/text_extractor/nodes/hitl_merge_node.py`

**Rules Added:**
- "EOD" (End of Day) = 23:59:59 (11:59 PM)
- "COB" (Close of Business) = 17:00:00 (5 PM)
- "by today" = 23:59:59 today
- "by tonight" = 23:59:59 today
- "midnight" = 23:59:59 (NOT 00:00:00)
- No time specified = 23:59:59 on that date

**Documentation:** See `docs/EOD_FIX.md` for complete details

---

## 🟠 HIGH PRIORITY

### 5. Redis Caching for Performance
**Status:** ✅ Implemented
**Effort:** Medium (2-3 days)
**Impact:** High

**Problem:** Every message triggers database queries for subscriber lists and recent tasks, causing high DB load

**Solution:** Implement Redis caching layer with cache-aside pattern

**Components Implemented:**
- ✅ Subscriber list caching (10 min TTL)
- ✅ Recent tasks caching (5 min TTL)
- ✅ User subscriptions caching (10 min TTL)
- ✅ Cache invalidation on subscribe/unsubscribe/task creation
- ✅ Graceful fallback to database on Redis errors

**Files modified:**
- `workers/text_extractor/services/redis_client.py` (added cache functions)
- `workers/text_extractor/services/database.py` (added caching to queries)
- `api_gateway/services/redis_client.py` (added async cache functions)
- `api_gateway/services/database.py` (added caching to queries)

**Cache Keys:**
- `cache:subscribers:{group_id}` - Subscriber list (TTL: 10 min)
- `cache:recent_tasks:{group_id}:{limit}` - Recent tasks (TTL: 5 min)
- `cache:user_subs:{user_id}` - User subscriptions (TTL: 10 min)

**Cache Invalidation:**
- Subscribe → Invalidates `cache:subscribers:{group_id}` + `cache:user_subs:{user_id}`
- Unsubscribe → Invalidates `cache:subscribers:{group_id}` + `cache:user_subs:{user_id}`
- Task creation → Invalidates `cache:recent_tasks:{group_id}:*`

**Performance Improvements:**
- 50-70% reduction in database queries (estimated)
- <10ms response time for cache hits (vs 50-100ms DB query)
- Better scalability for high-traffic groups

**Error Handling:**
- Redis connection failure → Falls back to database
- Serialization errors → Logs and skips cache
- Never fails requests due to cache issues

---

### 6. LLM Rate Limit Handling
### 6. LLM Rate Limit Handling
**Status:** ⏳ Planned
**Effort:** Medium (2 days)
**Impact:** High

**Problem:** Groq has 30 requests/minute limit, no backoff/retry logic

**Solution:** Implement exponential backoff with tenacity library

**Files to modify:**
- `workers/text_extractor/core/llm.py`
- `workers/text_extractor/requirements.txt`

---

### 7. Monitoring & Alerting (Prometheus/Grafana)
### 7. Monitoring & Alerting (Prometheus/Grafana)
**Status:** ✅ Implemented
**Effort:** High (1 week)
**Impact:** High

**Problem:** No visibility into system health, failures happen silently

**Solution:** Set up Grafana dashboards with Prometheus metrics

**Components:**
- ✅ Prometheus (scraping metrics from text_extractor and RabbitMQ)
- ✅ Grafana (visualization dashboards)
- ✅ Sieve Overview Dashboard (workflow metrics, HITL, DB performance)
- ✅ RabbitMQ Dashboard (queue depth, throughput)
- ⏳ Alerts (documented, not configured yet)

**Files created:**
- `monitoring/prometheus/prometheus.yml`
- `monitoring/grafana/provisioning/datasources/prometheus.yml`
- `monitoring/grafana/provisioning/dashboards/dashboard.yml`
- `monitoring/grafana/dashboards/sieve_overview.json`
- `monitoring/grafana/dashboards/rabbitmq_dashboard.json`
- `docs/MONITORING.md`
- `scripts/start_monitoring.sh`

**Access:**
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Dashboards auto-load on startup

**Metrics tracked:**
- Message processing rate
- Workflow latency (p50, p95)
- HITL trigger rate by error type
- Database operation latency
- Queue depth and throughput

---

### 8. Smart /start Command with Group Detection
### 8. Smart /start Command with Group Detection
**Status:** ⏳ Planned (Requires Telegram API Integration)
**Effort:** High (3-4 days)
**Impact:** Medium

**Problem:** Friends can't "re-add" bot to groups where it already exists (Telegram limitation)

**Current Solution:** 
- Deep link subscription works: When users click "Enable My Reminders" button in group
- `/start` command shows simple "Add to Group" button

**Ideal Solution (Future):**
- Detect if user is in groups with bot using Telegram API
- Show "Subscribe to Group X" buttons for existing groups
- Show "Add to New Group" button

**Implementation Required:**
```python
async def get_user_groups_with_bot(user_id: int) -> list:
    """Use Telegram getChatMember API to verify group membership"""
    # For each group where bot exists:
    #   - Call getChatMember API
    #   - Check if user is member/admin/creator
    #   - Return only groups where user has access
```

**Blocker:** Requires additional Telegram API calls (rate limits, complexity)

**Workaround:** Users should click "Enable My Reminders" button in group (works perfectly)

---

### 9. Unsubscribe Mechanism (Private Chat)
### 9. Unsubscribe Mechanism (Private Chat)
**Status:** ✅ Implemented
**Effort:** Low (1 day)
**Impact:** Medium

**Problem:** No way to unsubscribe (GDPR violation, bad UX)

**Solution:** `/unsubscribe` command in private chat with group selection buttons

**Files modified:**
- `api_gateway/routers/webhook.py`
- `api_gateway/services/database.py`

**Flow:**
1. User sends `/unsubscribe` to bot privately
2. Bot shows list of subscribed groups with inline buttons
3. User clicks group button (callback query)
4. Bot unsubscribes and confirms

**Implementation Details:**
- Uses inline keyboard with `callback_data: "unsub_{group_id}"`
- Callback query handler in webhook
- `unsubscribe_from_group()` function in database service
- Confirmation message sent after unsubscribe

---

### 10. Database Backup Strategy
### 10. Database Backup Strategy
**Status:** ⏳ Planned
**Effort:** Low (1 day)
**Impact:** High

**Problem:** Data only in Docker volume, no disaster recovery

**Solution:** Automated daily backups with retention policy

**Implementation:**
```bash
# Cron job (daily at 2 AM)
0 2 * * * docker exec sieve_postgres pg_dump -U user sieve | gzip > /backups/sieve_$(date +\%Y\%m\%d).sql.gz

# Retention: Keep last 30 days
find /backups -name "sieve_*.sql.gz" -mtime +30 -delete
```

---

## 🟡 MEDIUM PRIORITY

### 11. Task Update/Correction Detection (Deduplication)
### 11. Task Update/Correction Detection (Deduplication)
**Status:** ⏳ Planned
**Effort:** Medium (2-3 days)
**Impact:** Medium

**Problem:** When user sends correction message (e.g., "sorry, deadline is today not tomorrow"), system creates duplicate task instead of updating existing one

**Example:**
- Message 1: "Submit Morgan Stanley form by tomorrow EOD" → Task created (May 13)
- Message 2: "Sorry, Morgan Stanley form deadline today EOD" → **Duplicate task created** (May 11)
- Result: 2 tasks in database, user has to manually delete old one

**Root Cause:**
1. Intent node classifies correction as "NEW" instead of "UPDATE"
2. No UPDATE handler in workflow (UPDATE intent follows same path as NEW)
3. Context node only provides recent tasks as context, doesn't detect duplicates
4. No deduplication logic before saving

**Proposed Solution (Time Window Deduplication + Better Intent Detection):**

**Phase 1: Improve Intent Detection**
- Add UPDATE keywords to intent_node.py:
  - "sorry", "correction", "actually", "I meant", "change that to"
  - "no wait", "my bad", "wrong", "mistake", "oops"
- Update intent classification prompt to detect corrections

**Phase 2: Automatic Deduplication**
- Before saving task, check for similar task in last 5 minutes
- Use fuzzy title matching (80% similarity threshold)
- If found: Update existing task deadline
- If not found: Create new task

**Implementation:**
```python
# In main.py before save_task()
recent_similar_task = await find_recent_similar_task(
    user_id=user_id,
    group_id=group_id,
    title=extracted_data.title,
    time_window_minutes=5
)

if recent_similar_task:
    # Update existing task
    await update_task_deadline(
        task_id=recent_similar_task['id'],
        new_deadline=extracted_data.deadline
    )
    logger.info(f"[✓] Updated task {recent_similar_task['id']} (correction detected)")
else:
    # Create new task (normal flow)
    await save_tasks_atomic(...)
```

**Database Function:**
```python
async def find_recent_similar_task(user_id, group_id, title, time_window_minutes=5):
    """
    Find task with similar title created in last N minutes.
    Uses fuzzy matching (Levenshtein distance).
    """
    query = """
        SELECT id, title, deadline, created_at
        FROM tasks
        WHERE user_id = $1 
          AND group_id = $2
          AND created_at > NOW() - INTERVAL '{time_window_minutes} minutes'
        ORDER BY created_at DESC
        LIMIT 5
    """
    # Then apply fuzzy matching on titles
```

**Files to Modify:**
- `workers/text_extractor/nodes/intent_node.py` (add UPDATE keywords)
- `workers/text_extractor/main.py` (add deduplication logic)
- `workers/text_extractor/services/database.py` (add find_recent_similar_task, update_task_deadline)
- `workers/text_extractor/requirements.txt` (add python-Levenshtein for fuzzy matching)

**Alternative Approaches:**

**Option A: Manual Confirmation (More Control)**
- Detect similar task
- Send HITL: "Found similar task. Update or create new?"
- User chooses
- Pros: User has control
- Cons: Extra interaction, slower

**Option B: Longer Time Window (More Aggressive)**
- Use 30-minute window instead of 5 minutes
- Pros: Catches more corrections
- Cons: Might merge unrelated tasks

**Option C: Full UPDATE Workflow (Complete Solution)**
- Implement proper UPDATE intent handler
- Add task search/matching algorithm
- Add update confirmation flow
- Pros: Handles all update cases
- Cons: Complex, 1 week effort

**Recommended:** Start with Time Window Deduplication (5 min) + Better Intent Detection

**Benefits:**
- No more duplicate tasks for quick corrections
- Automatic (no user interaction needed)
- Simple implementation
- Safe (only merges very recent similar tasks)

**Risks:**
- Might merge tasks user didn't want merged (mitigated by short time window)
- Fuzzy matching might miss some corrections (can tune threshold)

---

### 12. Horizontal Scaling Support
### 12. Horizontal Scaling Support
**Status:** ⏳ Planned
**Effort:** High (1 week)
**Impact:** Medium

**Problem:** Single worker instance, no fault tolerance

**Solution:** Run multiple worker instances with distributed locking

**Requirements:**
- Distributed locks for HITL resolution
- Multiple text_extractor replicas
- Load balancing via RabbitMQ

---

### 13. Cron Job Reliability (Celery Beat)
### 13. Cron Job Reliability (Celery Beat)
**Status:** ⏳ Planned
**Effort:** Medium (3 days)
**Impact:** Medium

**Problem:** APScheduler shows "missed by 6 seconds" warnings

**Solution:** Replace APScheduler with Celery Beat

**Benefits:**
- Persistent task scheduling
- Better reliability under load
- Distributed task execution

---

### 14. Message Size Limits
### 14. Message Size Limits
**Status:** ⏳ Planned
**Effort:** Low (1 day)
**Impact:** Low

**Problem:** No limit on message length, can crash LLM API

**Solution:** Truncate messages to 2000 characters

---

### 15. Structured Logging
### 15. Structured Logging
**Status:** ⏳ Planned
**Effort:** Medium (2 days)
**Impact:** Medium

**Problem:** Print statements and basic logging, hard to debug

**Solution:** Use structlog for JSON logging

**Benefits:**
- Easy log aggregation (ELK stack)
- Better debugging
- Queryable logs

---

## 🟢 LOW PRIORITY

### 16. Task Editing/Deletion
### 16. Task Editing/Deletion
**Status:** ⏳ Planned
**Effort:** Medium (1 week)
**Impact:** Low

**Features:**
- `/tasks` - List your tasks
- `/delete <task_id>` - Delete a task
- `/edit <task_id>` - Edit deadline

---

### 17. Snooze Feature
### 17. Snooze Feature
**Status:** ⏳ Planned
**Effort:** Medium (1 week)
**Impact:** Low

**Feature:** Add inline buttons on reminders:
- [Snooze 1h]
- [Snooze 24h]
- [Mark Done]

---

### 18. Natural Language Deadline Parsing
### 18. Natural Language Deadline Parsing
**Status:** ⏳ Planned
**Effort:** Low (2 days)
**Impact:** Low

**Solution:** Use `dateparser` library as fallback to LLM

---

### 19. Group Name Storage
### 19. Group Name Storage
**Status:** ⏳ Planned
**Effort:** Low (1 day)
**Impact:** Low

**Solution:** Store group names in `group_subscriptions` table

---

### 20. Task Priority Levels
### 20. Task Priority Levels
**Status:** ⏳ Planned
**Effort:** Medium (3 days)
**Impact:** Low

**Feature:** LLM extracts priority (low/medium/high/urgent)

---

### 21. Recurring Tasks
### 21. Recurring Tasks
**Status:** ⏳ Planned
**Effort:** High (2 weeks)
**Impact:** Low

**Feature:** Support daily/weekly/monthly recurring tasks

---

### 22. Analytics Dashboard
### 22. Analytics Dashboard
**Status:** ⏳ Planned
**Effort:** High (1 week)
**Impact:** Low

**Metrics:**
- Tasks created per day
- HITL trigger rate
- Most active groups
- Reminder delivery success rate

---

### 23. Multi-Language Support
### 23. Multi-Language Support
**Status:** ⏳ Planned
**Effort:** High (2 weeks)
**Impact:** Low

**Feature:** Detect language and use appropriate LLM prompts

---

## Implementation Timeline

### Phase 1: Security & Reliability (Week 1) ✅ COMPLETED
- ✅ Webhook signature verification (optional mode)
- ✅ Database transactions
- ✅ Message deduplication
- ✅ Timezone conversion in code

### Phase 2: Operational Excellence (Week 2) ✅ COMPLETED
- ✅ Prometheus/Grafana monitoring
- ✅ Unsubscribe mechanism
- ✅ Redis caching (subscriber lists, recent tasks, user subscriptions)
- ✅ Kubernetes deployment with auto-scaling and monitoring
- ⏳ Smart /start command (requires Telegram API integration - deferred)
- ⏳ LLM rate limit handling (next)
- ⏳ Database backups (next)

### Phase 3: Scalability (Week 3)
- ⏳ Horizontal scaling support
- ⏳ Celery for cron jobs
- ⏳ Structured logging

### Phase 4: Features (Week 4+)
- ⏳ Task editing/deletion
- ⏳ Snooze feature
- ⏳ Analytics dashboard

---

## Notes

- All CRITICAL items must be completed before production deployment
- HIGH priority items should be completed within 2 weeks of launch
- MEDIUM and LOW priority items are enhancements for future iterations

Last Updated: 2026-05-22 (Phase 1 & 2 Complete - Redis Caching Implemented)
