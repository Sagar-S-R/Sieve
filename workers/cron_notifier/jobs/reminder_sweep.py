from workers.cron_notifier.services.database import get_due_tasks, mark_task_sent
from workers.cron_notifier.services.telegram_client import send_telegram_dm
from workers.cron_notifier.core.logger import logger


async def sweep_and_notify():
    """
    Main job: Check for due tasks and send reminders.
    
    This function:
    1. Queries database for tasks with deadline <= NOW() and is_sent = FALSE
    2. Sends a Telegram DM to each user
    3. Marks the task as sent in the database
    """
    logger.info("🔄 Starting reminder sweep...")
    
    try:
        # Get all due tasks
        tasks = await get_due_tasks()
        
        if not tasks:
            logger.info("✓ No due tasks found")
            return
        
        logger.info(f"📋 Found {len(tasks)} due task(s)")
        
        # Process each task
        for task in tasks:
            task_id = task['id']
            user_id = task['user_id']
            title = task['title']
            action_required = task['action_required']
            deadline = task['deadline']
            
            # Format reminder message
            message = (
                f"🔔 <b>Reminder</b>\n\n"
                f"📌 <b>{title}</b>\n"
                f"📝 {action_required}\n"
                f"⏰ Deadline: {deadline.strftime('%Y-%m-%d %H:%M')}"
            )
            
            logger.info(f"📤 Sending reminder for task {task_id} to user {user_id}")
            
            # Send DM
            success = await send_telegram_dm(user_id, message)
            
            if success:
                # Mark as sent in database
                marked = await mark_task_sent(task_id)
                if marked:
                    logger.info(f"✓ Task {task_id} marked as sent")
                else:
                    logger.warning(f"⚠ Failed to mark task {task_id} as sent (DM was sent)")
            else:
                logger.error(f"✗ Failed to send DM for task {task_id}")
        
        logger.info(f"✓ Sweep complete. Processed {len(tasks)} task(s)")
        
    except Exception as e:
        logger.error(f"✗ Error during sweep: {e}", exc_info=True)
