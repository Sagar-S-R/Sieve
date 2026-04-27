import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from workers.cron_notifier.jobs.reminder_sweep import sweep_and_notify
from workers.cron_notifier.services.database import init_pool, close_pool
from workers.cron_notifier.core.logger import logger


async def main():
    """
    Main entry point for cron_notifier.
    
    Initializes the database pool and starts the scheduler
    to run reminder sweeps every 60 seconds.
    """
    logger.info("🚀 Starting cron_notifier...")
    
    # Initialize database connection pool
    await init_pool()
    logger.info("✓ Database pool initialized")
    
    # Create scheduler
    scheduler = AsyncIOScheduler()
    
    # Add job to run every 60 seconds
    scheduler.add_job(
        sweep_and_notify,
        trigger='interval',
        seconds=60,
        id='reminder_sweep',
        name='Reminder Sweep Job',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("✓ Scheduler started (running every 60 seconds)")
    
    try:
        # Keep the event loop running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Shutting down...")
        scheduler.shutdown()
        await close_pool()
        logger.info("✓ Shutdown complete")


if __name__ == '__main__':
    asyncio.run(main())
