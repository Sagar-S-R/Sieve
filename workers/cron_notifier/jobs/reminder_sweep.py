from datetime import datetime, timedelta, timezone
from shared.database import (
    fetch_due_tasks_with_subscribers,
    increment_reminder_level
)
from workers.cron_notifier.services.telegram_client import send_telegram_dm
from workers.cron_notifier.core.logger import logger


async def sweep_and_notify():
    """
    Multi-level reminder sweep. One task row per group message;
    subscribers are resolved via JOIN in fetch_due_tasks_with_subscribers.

    Level 0 -> 1: 24-hour warning
    Level 1 -> 2: 1-hour final call
    Level 2 -> 3: Deadline alert
    """
    logger.info("Starting multi-level reminder sweep...")

    now = datetime.now(timezone.utc)

    try:
        tasks_24h = await fetch_due_tasks_with_subscribers(
            reminder_level=0,
            time_threshold=now + timedelta(hours=24)
        )
        tasks_1h = await fetch_due_tasks_with_subscribers(
            reminder_level=1,
            time_threshold=now + timedelta(hours=1)
        )
        tasks_due = await fetch_due_tasks_with_subscribers(
            reminder_level=2,
            time_threshold=now
        )

        all_tasks = tasks_24h + tasks_1h + tasks_due

        if not all_tasks:
            logger.info("No due tasks found")
            return

        logger.info(f"Found {len(all_tasks)} (task, subscriber) pairs to notify")

        # Track which task_ids we've already incremented this sweep
        incremented = set()

        for task in all_tasks:
            task_id = task["task_id"]
            user_id = task["user_id"]
            level = task["reminder_level"]

            if level == 0:
                urgency = "24-Hour Warning"
            elif level == 1:
                urgency = "1-Hour Final Call"
            else:
                urgency = "DEADLINE NOW"

            deadline = task.get("deadline")
            deadline_str = deadline.strftime("%Y-%m-%d %H:%M UTC") if deadline else "unknown"

            message = (
                f"*{urgency}*\n\n"
                f"*{task['title']}*\n"
                f"{task.get('action_required', '')}\n"
                f"Deadline: {deadline_str}"
            )

            success = await send_telegram_dm(user_id, message)

            if success:
                logger.info(f"[CRON] Reminder sent: task={task_id} user={user_id} level={level}")
                # Only increment once per task_id per sweep
                if task_id not in incremented:
                    await increment_reminder_level(task_id)
                    incremented.add(task_id)
            else:
                logger.error(f"[CRON] Failed to send reminder: task={task_id} user={user_id}")

        logger.info(f"Sweep complete. Processed {len(all_tasks)} notifications.")

    except Exception as e:
        logger.error(f"Error during sweep: {e}", exc_info=True)
