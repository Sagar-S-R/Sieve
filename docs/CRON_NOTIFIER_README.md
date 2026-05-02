# Cron Notifier - Lean Heartbeat Worker

## Overview

The **cron_notifier** is a standalone background process that wakes up every 60 seconds to send reminder DMs for tasks with arrived deadlines.

**No AI. No LangGraph. Just deterministic async Python.**

---

## Architecture

```

         AsyncIOScheduler                
    (runs every 60 seconds)              

               
               

      sweep_and_notify()                 
  1. Query PostgreSQL for due tasks      
  2. Send Telegram DM to each user       
  3. Mark task as sent in database       

```

---

## File Structure

```
workers/cron_notifier/
 core/
    config.py          # Pydantic BaseSettings (DATABASE_URL, TELEGRAM_BOT_TOKEN)
    logger.py          # Simple logging.basicConfig()
 services/
    database.py        # get_due_tasks() & mark_task_sent()
    telegram_client.py # send_telegram_dm()
 jobs/
    reminder_sweep.py  # Main sweep_and_notify() logic
 main.py                # Entry point with AsyncIOScheduler
 requirements.txt
 Dockerfile
```

---

## Key Functions

### `get_due_tasks()` - database.py
```sql
SELECT id, user_id, title, action_required, deadline
FROM tasks
WHERE deadline <= NOW() 
AND is_sent = FALSE
ORDER BY deadline ASC
```

### `mark_task_sent(task_id)` - database.py
```sql
UPDATE tasks 
SET is_sent = TRUE 
WHERE id = $1
```

### `send_telegram_dm(user_id, message_text)` - telegram_client.py
```python
POST https://api.telegram.org/bot<TOKEN>/sendMessage
{
  "chat_id": user_id,
  "text": message_text,
  "parse_mode": "HTML"
}
```

### `sweep_and_notify()` - reminder_sweep.py
```python
1. tasks = await get_due_tasks()
2. for task in tasks:
     message = format_reminder(task)
     success = await send_telegram_dm(user_id, message)
     if success:
         await mark_task_sent(task_id)
```

---

## Message Format

```
 Reminder

 Buy groceries
 Get milk, eggs, and bread from the store
 Deadline: 2026-04-28 15:00
```

---

## Database Schema Update

Added `is_sent` column to tasks table:

```sql
ALTER TABLE tasks ADD COLUMN is_sent BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_tasks_deadline_sent 
ON tasks(deadline, is_sent) 
WHERE is_sent = FALSE;
```

---

## Running the Worker

### Local Development
```bash
cd workers/cron_notifier
pip install -r requirements.txt
python main.py
```

### Docker
```bash
docker build -f workers/cron_notifier/Dockerfile -t cron_notifier .
docker run -e DATABASE_URL=... -e TELEGRAM_BOT_TOKEN=... cron_notifier
```

---

## Logging Output

```
2026-04-28 14:00:00 - cron_notifier - INFO -  Starting cron_notifier...
2026-04-28 14:00:00 - cron_notifier - INFO -  Database pool initialized
2026-04-28 14:00:00 - cron_notifier - INFO -  Scheduler started (running every 60 seconds)
2026-04-28 14:01:00 - cron_notifier - INFO -  Starting reminder sweep...
2026-04-28 14:01:00 - cron_notifier - INFO -  Found 3 due task(s)
2026-04-28 14:01:00 - cron_notifier - INFO -  Sending reminder for task 42 to user 123456
2026-04-28 14:01:01 - cron_notifier - INFO -  DM sent to user 123456
2026-04-28 14:01:01 - cron_notifier - INFO -  Task 42 marked as sent
2026-04-28 14:01:01 - cron_notifier - INFO -  Sweep complete. Processed 3 task(s)
```

---

## Code Metrics

| Metric | Value |
|--------|-------|
| Total Files | 8 |
| Lines of Code | ~200 |
| Dependencies | 5 |
| Complexity | Very Low |

**Philosophy:** Simple, deterministic, async. No over-engineering.

---

## Environment Variables

```env
DATABASE_URL=postgresql://user:password@postgres:5432/sieve
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

---

## Error Handling

- **Database errors**: Logged and sweep continues
- **Telegram API errors**: Logged, task NOT marked as sent (will retry next sweep)
- **Connection failures**: asyncpg handles reconnection automatically
- **Scheduler errors**: Logged, next sweep continues

---

## Testing

To test manually:
1. Insert a task with `deadline = NOW() - INTERVAL '1 minute'` and `is_sent = FALSE`
2. Wait for next sweep (max 60 seconds)
3. Check logs for DM sending confirmation
4. Verify `is_sent = TRUE` in database
5. Check Telegram for received DM

---

## Production Considerations

- **Idempotency**: Tasks are marked as sent immediately after DM success
- **Retry logic**: Failed DMs are NOT marked as sent, will retry next sweep
- **Performance**: Index on `(deadline, is_sent)` ensures fast queries
- **Monitoring**: All operations logged with clear emoji indicators
- **Graceful shutdown**: Handles SIGTERM/SIGINT properly

---

## Integration with Other Workers

```
text_extractor → PostgreSQL → cron_notifier → Telegram DM
media_extractor → PostgreSQL → cron_notifier → Telegram DM
```

The cron_notifier is completely decoupled - it only cares about:
1. Tasks in the database
2. Sending DMs via Telegram API

No dependencies on other workers.
