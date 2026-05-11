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
**Status:** 🚧 In Progress
**Effort:** Low (1 day)
**Impact:** Critical

**Problem:** Anyone can POST to `/webhook` endpoint and inject fake messages

**Solution:** Verify `X-Telegram-Bot-Api-Secret-Token` header on all webhook requests

**Files to modify:**
- `api_gateway/routers/webhook.py`

**Implementation:**
```python
def verify_telegram_signature(request: Request):
    secret_token = settings.TELEGRAM_BOT_TOKEN
    expected_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not hmac.compare_digest(expected_token or "", secret_token):
        raise HTTPException(status_code=403)
```

---

### 2. Database Transactions for Multi-Task Creation
**Status:** 🚧 In Progress
**Effort:** Low (1 day)
**Impact:** High

**Problem:** If task creation fails halfway through subscriber loop, partial data is saved

**Solution:** Wrap multi-task creation in atomic database transaction

**Files to modify:**
- `workers/text_extractor/main.py`
- `workers/text_extractor/services/database.py`

**Implementation:**
```python
async with conn.transaction():
    for subscriber_id in subscribers:
        await save_task(task_data)
```

---

### 3. Message Deduplication (Idempotency)
**Status:** 🚧 In Progress
**Effort:** Medium (2 days)
**Impact:** High

**Problem:** If Telegram webhook retries, same message gets processed twice

**Solution:** Track processed message IDs in Redis with TTL

**Files to modify:**
- `api_gateway/routers/webhook.py`
- `workers/text_extractor/main.py`
- `workers/text_extractor/services/redis_client.py`

**Implementation:**
```python
def is_already_processed(message_id, group_id):
    key = f"processed:{group_id}:{message_id}"
    if redis_client.exists(key):
        return True
    redis_client.setex(key, 3600, "1")
    return False
```

---

### 4. Timezone Conversion in Code (Not LLM)
**Status:** 🚧 In Progress
**Effort:** Low (1 day)
**Impact:** High

**Problem:** LLM can miscalculate IST to UTC conversion (5.5 hour offset)

**Solution:** Do timezone conversion in Python after LLM extraction

**Files to modify:**
- `workers/text_extractor/nodes/extractor_node.py`
- `workers/text_extractor/main.py`

**Implementation:**
```python
from datetime import timezone, timedelta

def convert_ist_to_utc(ist_datetime_str):
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ist_dt = datetime.fromisoformat(ist_datetime_str).replace(tzinfo=ist_tz)
    return ist_dt.astimezone(timezone.utc)
```

---

## 🟠 HIGH PRIORITY

### 5. LLM Rate Limit Handling
**Status:** ⏳ Planned
**Effort:** Medium (2 days)
**Impact:** High

**Problem:** Groq has 30 requests/minute limit, no backoff/retry logic

**Solution:** Implement exponential backoff with tenacity library

**Files to modify:**
- `workers/text_extractor/core/llm.py`
- `workers/text_extractor/requirements.txt`

---

### 6. Monitoring & Alerting (Prometheus/Grafana)
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

### 7. Unsubscribe Mechanism (Private Chat)
**Status:** 🚧 In Progress
**Effort:** Low (1 day)
**Impact:** Medium

**Problem:** No way to unsubscribe (GDPR violation, bad UX)

**Solution:** `/unsubscribe` command in private chat with group selection buttons

**Files to modify:**
- `api_gateway/routers/webhook.py`
- `api_gateway/services/database.py`

**Flow:**
1. User sends `/unsubscribe` to bot privately
2. Bot shows list of subscribed groups with buttons
3. User clicks group button
4. Bot unsubscribes and confirms

---

### 8. Database Backup Strategy
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

### 9. Horizontal Scaling Support
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

### 10. Cron Job Reliability (Celery Beat)
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

### 11. Message Size Limits
**Status:** ⏳ Planned
**Effort:** Low (1 day)
**Impact:** Low

**Problem:** No limit on message length, can crash LLM API

**Solution:** Truncate messages to 2000 characters

---

### 12. Structured Logging
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

### 13. Task Editing/Deletion
**Status:** ⏳ Planned
**Effort:** Medium (1 week)
**Impact:** Low

**Features:**
- `/tasks` - List your tasks
- `/delete <task_id>` - Delete a task
- `/edit <task_id>` - Edit deadline

---

### 14. Snooze Feature
**Status:** ⏳ Planned
**Effort:** Medium (1 week)
**Impact:** Low

**Feature:** Add inline buttons on reminders:
- [Snooze 1h]
- [Snooze 24h]
- [Mark Done]

---

### 15. Natural Language Deadline Parsing
**Status:** ⏳ Planned
**Effort:** Low (2 days)
**Impact:** Low

**Solution:** Use `dateparser` library as fallback to LLM

---

### 16. Group Name Storage
**Status:** ⏳ Planned
**Effort:** Low (1 day)
**Impact:** Low

**Solution:** Store group names in `group_subscriptions` table

---

### 17. Task Priority Levels
**Status:** ⏳ Planned
**Effort:** Medium (3 days)
**Impact:** Low

**Feature:** LLM extracts priority (low/medium/high/urgent)

---

### 18. Recurring Tasks
**Status:** ⏳ Planned
**Effort:** High (2 weeks)
**Impact:** Low

**Feature:** Support daily/weekly/monthly recurring tasks

---

### 19. Analytics Dashboard
**Status:** ⏳ Planned
**Effort:** High (1 week)
**Impact:** Low

**Metrics:**
- Tasks created per day
- HITL trigger rate
- Most active groups
- Reminder delivery success rate

---

### 20. Multi-Language Support
**Status:** ⏳ Planned
**Effort:** High (2 weeks)
**Impact:** Low

**Feature:** Detect language and use appropriate LLM prompts

---

## Implementation Timeline

### Phase 1: Security & Reliability (Week 1)
- ✅ Webhook signature verification
- ✅ Database transactions
- ✅ Message deduplication
- ✅ Timezone conversion in code

### Phase 2: Operational Excellence (Week 2)
- ✅ Prometheus/Grafana monitoring
- ✅ Unsubscribe mechanism
- ⏳ LLM rate limit handling
- ⏳ Database backups

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

Last Updated: 2026-05-10
