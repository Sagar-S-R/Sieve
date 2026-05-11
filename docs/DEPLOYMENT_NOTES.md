# Deployment Notes - May 11, 2026

## Changes Made

### 1. Simplified /start Command

**File:** `api_gateway/routers/webhook.py`

**What changed:**
- Removed complex group detection logic (was unreliable)
- Simplified to show basic welcome message with "Add to Group" button
- Deep link subscription still works perfectly (when users click group button)

**Why:**
- `get_user_available_groups()` doesn't verify actual group membership
- Would require Telegram API calls to properly verify (complex, rate limits)
- Current workaround (click group button) works perfectly

**User flow:**
1. Bot added to group → Welcome message with "Enable My Reminders" button
2. User clicks button → Opens private chat with deep link
3. Bot auto-subscribes user → Done! ✅

---

## To Deploy

### Rebuild API Gateway

```bash
docker-compose up -d --build api_gateway
```

### Verify Changes

```bash
# Check logs
docker-compose logs api_gateway --tail 50

# Test /start command
# 1. Send /start to bot privately
# 2. Should see simple welcome message with "Add to Group" button
# 3. Deep link subscription should still work
```

---

## Current Status

### ✅ Working Features

1. **Deep Link Subscription** (Primary method)
   - User clicks "Enable My Reminders" in group
   - Opens private chat with `/start sub_{group_id}`
   - Auto-subscribes user
   - **This is the recommended method!**

2. **Unsubscribe Mechanism**
   - `/unsubscribe` command in private chat
   - Shows list of subscribed groups
   - Click to unsubscribe

3. **All Critical Features**
   - Webhook signature verification
   - Database transactions
   - Message deduplication
   - Timezone conversion
   - Prometheus/Grafana monitoring

### ⏳ Deferred Features

1. **Smart /start with Group Detection**
   - Requires Telegram API integration
   - Complex implementation (3-4 days)
   - Low priority (workaround exists)
   - See `docs/IMPROVEMENTS.md` item #7

---

## User Instructions

### For New Users

**Recommended method:**
1. Look for bot's welcome message in group
2. Click "🔔 Enable My Reminders" button
3. Done!

**Alternative method:**
1. Send `/start` to bot privately
2. Click "➕ Add to Group"
3. Select your group

**Note:** If bot already in group, use recommended method (click group button)

---

## Documentation Created

1. **`docs/USER_GUIDE.md`**
   - Complete user guide
   - How to subscribe, use commands
   - Troubleshooting tips
   - Multi-subscriber system explained

2. **`docs/FRIEND_SUBSCRIPTION_SOLUTION.md`**
   - Explains the "re-add bot" issue
   - Why it happens (Telegram limitation)
   - Current solution (deep link)

3. **`docs/USER_ONBOARDING_FLOW.md`**
   - Technical flow diagrams
   - Deep link formats
   - Implementation details

4. **`docs/IMPROVEMENTS.md`**
   - Updated status for all features
   - Phase 1 & 2 mostly complete
   - Smart /start marked as deferred

---

## Next Steps

### High Priority

1. **LLM Rate Limit Handling**
   - Implement exponential backoff
   - Use tenacity library
   - Prevent Groq 429 errors

2. **Database Backups**
   - Daily automated backups
   - 30-day retention
   - Disaster recovery plan

### Medium Priority

3. **Horizontal Scaling**
   - Multiple worker instances
   - Distributed HITL locks
   - Load balancing

4. **Structured Logging**
   - Replace print statements
   - Use structlog for JSON logs
   - Better debugging

### Low Priority

5. **Task Editing/Deletion**
   - `/tasks` command
   - `/delete` command
   - `/edit` command

6. **Snooze Feature**
   - Inline buttons on reminders
   - Snooze 1h, 24h options

---

## Known Limitations

### 1. Group Detection in /start

**Issue:** Can't reliably detect which groups user is in

**Reason:** Would require Telegram API calls for each group

**Workaround:** Users click "Enable My Reminders" button in group

**Future:** May implement with proper Telegram API integration

### 2. No Task Editing

**Issue:** Can't edit task deadlines after creation

**Workaround:** Unsubscribe and re-subscribe, mention task again

**Future:** `/edit` command planned

### 3. No Recurring Tasks

**Issue:** Can't set "every Monday at 9am" tasks

**Workaround:** Mention task each time

**Future:** Recurring task support planned

---

## Testing Checklist

Before deploying to production:

- [ ] Rebuild api_gateway: `docker-compose up -d --build api_gateway`
- [ ] Test /start command (should show simple welcome)
- [ ] Test deep link subscription (click group button)
- [ ] Test /unsubscribe command
- [ ] Test task extraction with keywords
- [ ] Test HITL clarification flow
- [ ] Test multi-subscriber task creation
- [ ] Check Prometheus metrics: http://localhost:9090
- [ ] Check Grafana dashboards: http://localhost:3000
- [ ] Check RabbitMQ queue depth
- [ ] Verify timezone conversion (IST→UTC)
- [ ] Test message deduplication

---

## Rollback Plan

If issues occur after deployment:

```bash
# Stop services
docker-compose down

# Restore previous version
git checkout <previous-commit>

# Rebuild and restart
docker-compose up -d --build

# Verify
docker-compose logs -f
```

---

## Monitoring

### Key Metrics to Watch

1. **Message Processing Rate**
   - Normal: 10-50 messages/minute
   - Alert if: >100 messages/minute (spam?)

2. **Workflow Latency**
   - Normal: p95 < 5 seconds
   - Alert if: p95 > 10 seconds

3. **HITL Trigger Rate**
   - Normal: 10-20% of messages
   - Alert if: >50% (prompt issues?)

4. **Database Latency**
   - Normal: <100ms
   - Alert if: >500ms

5. **Queue Depth**
   - Normal: 0-10 messages
   - Alert if: >100 messages (worker down?)

### Grafana Dashboards

- **Sieve Overview**: http://localhost:3000/d/sieve-overview
- **RabbitMQ**: http://localhost:3000/d/rabbitmq-dashboard

---

## Support

### If Something Breaks

1. Check logs: `docker-compose logs -f`
2. Check Grafana dashboards
3. Check RabbitMQ management: http://localhost:15672
4. Restart services: `docker-compose restart`
5. Full rebuild: `docker-compose down && docker-compose up -d --build`

### Contact

- Developer: [Your contact]
- GitHub: [Repository URL]
- Documentation: `docs/` folder

---

Last Updated: 2026-05-11
Status: Ready for deployment (rebuild api_gateway required)
