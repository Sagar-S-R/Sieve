from datetime import datetime
from typing import Optional
import asyncpg
from workers.cron_notifier.core.config import settings

_pool: Optional[asyncpg.Pool] = None


async def init_pool():
    """Initialize database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )


async def close_pool():
    """Close database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetch_due_tasks_with_subscribers(reminder_level: int, time_threshold: datetime) -> list:
    """
    Fetch tasks due within threshold joined with who to notify.
    Group tasks: JOIN with group_subscriptions.
    Personal tasks: notify owner directly.
    Returns one row per (task, notify_user) pair.
    """
    if _pool is None:
        await init_pool()

    async with _pool.acquire() as conn:
        rows = await conn.fetch("""
            -- Group tasks: fan out to all subscribers
            SELECT
                t.id as task_id,
                t.group_id,
                t.title,
                t.action_required,
                t.deadline,
                t.reminder_level,
                t.reminder_strategy,
                t.location,
                t.form_url,
                gs.subscriber_id as user_id
            FROM tasks t
            JOIN group_subscriptions gs ON t.group_id = gs.group_id
            WHERE t.group_id IS NOT NULL
            AND t.reminder_level = $1
            AND t.deadline <= $2

            UNION ALL

            -- Personal tasks: notify the owner directly
            SELECT
                t.id as task_id,
                t.group_id,
                t.title,
                t.action_required,
                t.deadline,
                t.reminder_level,
                t.reminder_strategy,
                t.location,
                t.form_url,
                t.user_id as user_id
            FROM tasks t
            WHERE t.user_id IS NOT NULL
            AND t.group_id IS NULL
            AND t.reminder_level = $1
            AND t.deadline <= $2

            ORDER BY deadline ASC
        """, reminder_level, time_threshold)
        return [dict(r) for r in rows]


async def increment_reminder_level(task_id: int):
    """Increment reminder_level by 1 for a task."""
    if _pool is None:
        await init_pool()

    async with _pool.acquire() as conn:
        await conn.execute("""
            UPDATE tasks
            SET reminder_level = reminder_level + 1,
                updated_at = NOW()
            WHERE id = $1
        """, task_id)
