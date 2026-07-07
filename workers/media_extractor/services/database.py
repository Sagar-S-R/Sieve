"""Database service for media_extractor worker."""
import asyncpg
from typing import Optional
from workers.media_extractor.core.config import settings

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


async def get_group_subscribers(group_id: int) -> list:
    """Get all subscriber IDs for a group."""
    if _pool is None:
        await init_pool()
    try:
        async with _pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT subscriber_id FROM group_subscriptions
                WHERE group_id = $1
                ORDER BY subscribed_at ASC
            """, group_id)
            return [r['subscriber_id'] for r in rows]
    except Exception as e:
        print(f"[DB] get_group_subscribers error: {e}")
        return []


async def save_tasks_atomic(subscribers: list, group_id: int, message_sender_id: int,
                            title: str, action_required: str, deadline) -> list:
    """Save tasks for all subscribers atomically in a single transaction."""
    if _pool is None:
        await init_pool()

    from datetime import datetime
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))

    try:
        async with _pool.acquire() as conn:
            task_ids = []
            async with conn.transaction():
                for subscriber_id in subscribers:
                    task_id = await conn.fetchval("""
                        INSERT INTO tasks (
                            user_id, group_id, message_sender_id, title,
                            action_required, deadline, reminder_level
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, 0)
                        RETURNING id
                    """,
                        subscriber_id, group_id, message_sender_id,
                        title, action_required, deadline
                    )
                    task_ids.append(task_id)
            return task_ids
    except Exception as e:
        print(f"[DB] save_tasks_atomic error: {e}")
        raise


async def save_task(task_data: dict):
    """
    Save a single task to the database.
    Kept for backward compatibility.
    """
    if _pool is None:
        await init_pool()

    from datetime import datetime
    deadline = task_data.get('deadline')
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))

    try:
        async with _pool.acquire() as conn:
            task_id = await conn.fetchval("""
                INSERT INTO tasks (user_id, group_id, title, action_required, deadline, reminder_level)
                VALUES ($1, $2, $3, $4, $5, 0)
                RETURNING id
            """,
                task_data.get('user_id'),
                task_data.get('group_id'),
                task_data.get('title'),
                task_data.get('action_required'),
                deadline,
            )
            print(f"[DB] Task saved: {task_id}")
            return task_id
    except Exception as e:
        print(f"[DB] save_task error: {e}")
        raise
