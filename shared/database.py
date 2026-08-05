import os
import time
from datetime import datetime, timezone
from typing import Optional
import asyncpg
import logging

from shared.metrics import db_operation_latency

logger = logging.getLogger(__name__)

# Connection pool singleton
_pool: Optional[asyncpg.Pool] = None


async def init_pool(min_size: int = 5, max_size: int = 20):
    """Initialize database connection pool."""
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL")
        _pool = await asyncpg.create_pool(
            db_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60
        )
        logger.info(f"[DB] Connection pool initialized (min={min_size}, max={max_size})")


async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool lazily."""
    global _pool
    if _pool is None:
        await init_pool(min_size=2, max_size=10)
    return _pool


async def close_pool():
    """Close database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        logger.info("[DB] Connection pool closed")
        _pool = None


# ============================================================================
# SUBSCRIPTIONS (API Gateway / Media Extractor)
# ============================================================================

async def subscribe_to_group(group_id: int, subscriber_id: int) -> bool:
    from shared.redis_client import invalidate_subscribers_cache, invalidate_user_subs_cache
    pool = await get_pool()
    query = """
        INSERT INTO group_subscriptions (group_id, subscriber_id)
        VALUES ($1, $2)
        ON CONFLICT (group_id, subscriber_id) DO NOTHING
        RETURNING id
    """
    try:
        async with pool.acquire() as conn:
            await conn.fetchval(query, group_id, subscriber_id)
            await invalidate_subscribers_cache(group_id)
            await invalidate_user_subs_cache(subscriber_id)
            return True
    except Exception as e:
        logger.error(f"[DB] Error subscribing user {subscriber_id} to group {group_id}: {e}")
        return False


async def unsubscribe_from_group(group_id: int, subscriber_id: int) -> bool:
    from shared.redis_client import invalidate_subscribers_cache, invalidate_user_subs_cache
    pool = await get_pool()
    query = """
        DELETE FROM group_subscriptions
        WHERE group_id = $1 AND subscriber_id = $2
        RETURNING id
    """
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, group_id, subscriber_id)
            if result is not None:
                await invalidate_subscribers_cache(group_id)
                await invalidate_user_subs_cache(subscriber_id)
            return result is not None
    except Exception as e:
        logger.error(f"[DB] Error unsubscribing user {subscriber_id} from group {group_id}: {e}")
        return False


async def get_group_subscribers(group_id: int) -> list:
    from shared.redis_client import get_cached_subscribers, set_cached_subscribers
    cached = await get_cached_subscribers(group_id)
    if cached is not None:
        return cached

    pool = await get_pool()
    query = """
        SELECT subscriber_id FROM group_subscriptions
        WHERE group_id = $1 ORDER BY subscribed_at ASC
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, group_id)
            subscribers = [row['subscriber_id'] for row in rows]
            await set_cached_subscribers(group_id, subscribers)
            return subscribers
    except Exception as e:
        logger.error(f"[DB] Error fetching subscribers for group {group_id}: {e}")
        return []


async def get_user_subscriptions(user_id: int) -> list:
    from shared.redis_client import get_cached_user_subs, set_cached_user_subs
    cached = await get_cached_user_subs(user_id)
    if cached is not None:
        return cached

    pool = await get_pool()
    query = """
        SELECT group_id, subscribed_at FROM group_subscriptions
        WHERE subscriber_id = $1 ORDER BY subscribed_at DESC
    """
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            subs = [{'group_id': row['group_id'], 'subscribed_at': row['subscribed_at']} for row in rows]
            await set_cached_user_subs(user_id, subs)
            return subs
    except Exception as e:
        logger.error(f"[DB] Error fetching subscriptions for user {user_id}: {e}")
        return []


# ============================================================================
# TASK CREATION & UPDATES (Text / Media Extractors)
# ============================================================================

async def save_task(task_data: dict) -> int:
    """Save a single task. Supports both group tasks and personal tasks."""
    start = time.time()
    try:
        pool = await get_pool()
        deadline = task_data.get('deadline')
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))

        applies_at = task_data.get('applies_at')
        if isinstance(applies_at, str):
            applies_at = datetime.fromisoformat(applies_at.replace('Z', '+00:00'))

        async with pool.acquire() as conn:
            task_id = await conn.fetchval("""
                INSERT INTO tasks (
                    group_id, user_id, message_sender_id, title, action_required,
                    deadline, source_message_text, message_type,
                    applies_at, location, form_url, reminder_strategy, reminder_level
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,0)
                RETURNING id
            """,
                task_data.get('group_id'),
                task_data.get('user_id'),
                task_data.get('message_sender_id'),
                task_data.get('title'),
                task_data.get('action_required'),
                deadline,
                task_data.get('source_message_text'),
                task_data.get('message_type', 'deadline'),
                applies_at,
                task_data.get('location'),
                task_data.get('form_url'),
                task_data.get('reminder_strategy', 'standard')
            )
            logger.info(f"[DB] Task saved: {task_id}")

            from shared.redis_client import invalidate_recent_tasks_cache
            if task_data.get('group_id'):
                await invalidate_recent_tasks_cache(task_data.get('group_id'))

            return task_id
    except Exception as e:
        logger.error(f"[DB] save_task error: {e}", exc_info=True)
        raise
    finally:
        db_operation_latency.labels(operation="save_task").observe(time.time() - start)


async def save_tasks_atomic(subscribers: list, group_id: int, message_sender_id: int,
                            title: str, action_required: str, deadline) -> list:
    """Save tasks for all subscribers atomically in a single transaction (Media Extractor)."""
    pool = await get_pool()
    if isinstance(deadline, str):
        deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))

    try:
        async with pool.acquire() as conn:
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
            
            from shared.redis_client import invalidate_recent_tasks_cache
            await invalidate_recent_tasks_cache(group_id)
            
            return task_ids
    except Exception as e:
        logger.error(f"[DB] save_tasks_atomic error: {e}")
        raise


async def update_task_by_id(task_id: int, new_deadline=None, new_location: str = None) -> bool:
    """Update a specific task by ID."""
    if isinstance(new_deadline, str):
        new_deadline = datetime.fromisoformat(new_deadline.replace('Z', '+00:00'))

    start = time.time()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE tasks
                SET deadline = COALESCE($1, deadline),
                    location = COALESCE($2, location),
                    updated_at = NOW()
                WHERE id = $3
            """, new_deadline, new_location, task_id)
            success = result == "UPDATE 1"
            return success
    except Exception as e:
        logger.error(f"[DB] update_task_by_id error: {e}", exc_info=True)
        return False
    finally:
        db_operation_latency.labels(operation="update_task_by_id").observe(time.time() - start)


async def update_task_deadline(task_id: int, user_id: int, new_deadline, group_id: int) -> bool:
    """Update task deadline with ownership check (API Gateway)."""
    from shared.redis_client import invalidate_recent_tasks_cache_async
    pool = await get_pool()
    if isinstance(new_deadline, str):
        new_deadline = datetime.fromisoformat(new_deadline.replace('Z', '+00:00'))
    
    query = """
        UPDATE tasks SET deadline = $1, updated_at = NOW()
        WHERE id = $2 AND user_id = $3 RETURNING id
    """
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, new_deadline, task_id, user_id)
            if result:
                await invalidate_recent_tasks_cache_async(group_id)
                return True
            return False
    except Exception as e:
        logger.error(f"[DB] Error updating task {task_id}: {e}")
        return False


async def delete_task(task_id: int, user_id: int) -> Optional[dict]:
    """Delete a task with ownership check (API Gateway)."""
    from shared.redis_client import invalidate_recent_tasks_cache_async
    pool = await get_pool()
    query = "DELETE FROM tasks WHERE id = $1 AND user_id = $2 RETURNING id, title, deadline, group_id"
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id, user_id)
            if row:
                task = dict(row)
                await invalidate_recent_tasks_cache_async(task['group_id'])
                return task
            return None
    except Exception as e:
        logger.error(f"[DB] Error deleting task {task_id}: {e}")
        return None


# ============================================================================
# TASK QUERYING (All Services)
# ============================================================================

async def fetch_recent_tasks(group_id: int, limit: int = 10, excluded_task_ids: list = []) -> list:
    """Fetch recent tasks with caching and exclusion support (Text Extractor)."""
    from shared.redis_client import get_cached_recent_tasks, set_cached_recent_tasks

    if not excluded_task_ids:
        cached = await get_cached_recent_tasks(group_id, limit)
        if cached is not None:
            return cached

    start = time.time()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            if excluded_task_ids:
                rows = await conn.fetch("""
                    SELECT id, group_id, title, action_required,
                           deadline, source_message_text, message_type, created_at,
                           location, form_url
                    FROM tasks WHERE group_id = $1 AND id != ALL($3)
                    ORDER BY created_at DESC LIMIT $2
                """, group_id, limit, excluded_task_ids)
            else:
                rows = await conn.fetch("""
                    SELECT id, group_id, title, action_required,
                           deadline, source_message_text, message_type, created_at,
                           location, form_url
                    FROM tasks WHERE group_id = $1
                    ORDER BY created_at DESC LIMIT $2
                """, group_id, limit)

            result = [dict(r) for r in rows]
            if not excluded_task_ids:
                await set_cached_recent_tasks(group_id, limit, result)
            return result
    except Exception as e:
        logger.error(f"[DB] fetch_recent_tasks error: {e}", exc_info=True)
        return []
    finally:
        db_operation_latency.labels(operation="fetch_recent_tasks").observe(time.time() - start)


async def get_task_by_id(task_id: int) -> Optional[dict]:
    pool = await get_pool()
    query = "SELECT id, user_id, group_id, title, action_required, deadline, created_at FROM tasks WHERE id = $1"
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"[DB] Error fetching task {task_id}: {e}")
        return None


async def get_user_tasks(user_id: int) -> dict:
    pool = await get_pool()
    query = "SELECT id, user_id, group_id, title, action_required, deadline, created_at FROM tasks WHERE user_id = $1 ORDER BY deadline ASC"
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            now = datetime.now(timezone.utc)
            upcoming, overdue = [], []
            for row in rows:
                task = dict(row)
                if task['deadline'] > now:
                    upcoming.append(task)
                else:
                    overdue.append(task)
            return {'upcoming': upcoming, 'overdue': overdue}
    except Exception as e:
        logger.error(f"[DB] Error fetching tasks for user {user_id}: {e}")
        return {'upcoming': [], 'overdue': []}


async def search_tasks_by_title_fuzzy(group_id: int, search_title: str, limit: int = 5, excluded_task_ids: list = []) -> list:
    """Fuzzy search for tasks by title with exclusion support (Text Extractor)."""
    start_time = time.time()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            if excluded_task_ids:
                query = """
                    SELECT id, group_id, title, action_required, deadline, created_at, similarity(LOWER(title), LOWER($2)) AS similarity
                    FROM tasks WHERE group_id = $1 AND deadline > NOW() - INTERVAL '7 days' AND id != ALL($4) AND similarity(LOWER(title), LOWER($2)) > 0.3
                    ORDER BY similarity DESC LIMIT $3
                """
                rows = await conn.fetch(query, group_id, search_title, limit, excluded_task_ids)
            else:
                query = """
                    SELECT id, group_id, title, action_required, deadline, created_at, similarity(LOWER(title), LOWER($2)) AS similarity
                    FROM tasks WHERE group_id = $1 AND deadline > NOW() - INTERVAL '7 days' AND similarity(LOWER(title), LOWER($2)) > 0.3
                    ORDER BY similarity DESC LIMIT $3
                """
                rows = await conn.fetch(query, group_id, search_title, limit)
            result = [dict(row) for row in rows]
            return result
    except Exception as e:
        logger.error(f"[DB] Error in fuzzy search: {e}", exc_info=True)
        return []
    finally:
        db_operation_latency.labels(operation="search_tasks_by_title_fuzzy").observe(time.time() - start_time)


# ============================================================================
# CRON NOTIFIER OPERATIONS
# ============================================================================

async def fetch_due_tasks_with_subscribers(reminder_level: int, time_threshold: datetime) -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT t.id as task_id, t.group_id, t.title, t.action_required,
                   t.deadline, t.reminder_level, t.reminder_strategy, t.location, t.form_url,
                   gs.subscriber_id as user_id
            FROM tasks t
            JOIN group_subscriptions gs ON t.group_id = gs.group_id
            WHERE t.group_id IS NOT NULL AND t.reminder_level = $1 AND t.deadline <= $2
            UNION ALL
            SELECT t.id as task_id, t.group_id, t.title, t.action_required,
                   t.deadline, t.reminder_level, t.reminder_strategy, t.location, t.form_url,
                   t.user_id as user_id
            FROM tasks t
            WHERE t.user_id IS NOT NULL AND t.group_id IS NULL AND t.reminder_level = $1 AND t.deadline <= $2
            ORDER BY deadline ASC
        """, reminder_level, time_threshold)
        return [dict(r) for r in rows]


async def increment_reminder_level(task_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE tasks SET reminder_level = reminder_level + 1, updated_at = NOW() WHERE id = $1", task_id)
