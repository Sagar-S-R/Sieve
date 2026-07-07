from workers.cron_notifier.services.database import get_due_tasks, update_reminder_level
from workers.cron_notifier.services.telegram_client import send_telegram_dm
from workers.cron_notifier.core.logger import logger


async def sweep_and_notify():
    """
    Multi-level reminder system with anticipatory intelligence.
    
    This function implements a 3-stage notification strategy:
    1. Level 0 → 1: 24-hour warning (proactive)
    2. Level 1 → 2: 1-hour final call (urgent)
    3. Level 2 → 3: Deadline alert (critical)
    
    After level 3, tasks are archived (no more reminders).
    """
    logger.info(" Starting multi-level reminder sweep...")
    
    try:
        # Get all tasks across all reminder windows
        tasks = await get_due_tasks()
        
        if not tasks:
            logger.info("✓ No due tasks found")
            return
        
        logger.info(f" Found {len(tasks)} task(s) across all windows")
        
        # Process each task based on its window
        for task in tasks:
            task_id = task['id']
            user_id = task['user_id']
            title = task['title']
            action_required = task['action_required']
            deadline = task['deadline']
            current_level = task['reminder_level']
            window = task['window']
            
            # Determine message based on window
            if window == '24h':
                emoji = ""
                urgency = "24-Hour Warning"
                next_level = 1
            elif window == '1h':
                emoji = ""
                urgency = "1-Hour Final Call"
                next_level = 2
            else:  # 'now'
                emoji = ""
                urgency = "DEADLINE NOW"
                next_level = 3
            
            # Format reminder message
            message = (
                f"{emoji} <b>{urgency}</b>\n\n"
                f" <b>{title}</b>\n"
                f" {action_required}\n"
                f" Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}"
            )
            
            logger.info(f" Sending {window} reminder for task {task_id} to user {user_id}")
            
            # Send DM
            success = await send_telegram_dm(user_id, message)
            
            if success:
                # Update reminder level
                updated = await update_reminder_level(task_id, next_level)
                if updated:
                    logger.info(f"✓ Task {task_id} updated to level {next_level}")
                else:
                    logger.warning(f" Failed to update task {task_id} level (DM was sent)")
            else:
                logger.error(f"✗ Failed to send DM for task {task_id}")
        
        logger.info(f"✓ Sweep complete. Processed {len(tasks)} task(s)")
        
    except Exception as e:
        logger.error(f"✗ Error during sweep: {e}", exc_info=True)
