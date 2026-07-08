"""Database service with asyncpg connection pool."""
import time
from datetime import datetime
import asyncpg
from workers.text_extractor.core.config import settings
from workers.text_extractor.core.metrics import db_operation_latency
from workers.text_extractor.core.logger import logger

pool = None


async def init_pool(min_size: int = 5, max_size: int = 20):
    """Initialize database connection pool."""
    global pool
    pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=min_size,
        max_size=max_size
    )
    logger.info(f"[DB] Connection pool initialized (min={min_size}, max={max_size})")


async def close_pool():
    """Close database connection pool."""
    global pool
    if pool:
        await pool.close()
        logger.info("[DB] Connection pool closed")


async def fetch_recent_tasks(group_id: int, limit: int = 10, excluded_task_ids: list = []) -> list:
    """Fetch recent tasks with caching and exclusion support."""
    from workers.text_extractor.services.redis_client import get_cached_recent_tasks, set_cached_recent_tasks

    # Only use cache if no exclusions
    if not excluded_task_ids:
        cached = get_cached_recent_tasks(group_id, limit)
        if cached is not None:
            logger.info(f"[CACHE HIT] recent_tasks:{group_id}:{limit}")
            return cached

    logger.info(f"[CACHE MISS] recent_tasks:{group_id}:{limit}")
    start = time.time()
    try:
        async with pool.acquire() as conn:
            if excluded_task_ids:
                rows = await conn.fetch("""
                    SELECT id, group_id, title, action_required,
                           deadline, source_message_text, message_type, created_at,
                           location, form_url
                    FROM tasks
                    WHERE group_id = $1
                      AND id != ALL($3)
                    ORDER BY created_at DESC
                    LIMIT $2
                """, group_id, limit, excluded_task_ids)
            else:
                rows = await conn.fetch("""
                    SELECT id, group_id, title, action_required,
                           deadline, source_message_text, message_type, created_at,
                           location, form_url
                    FROM tasks
                    WHERE group_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, group_id, limit)

            result = [dict(r) for r in rows]

            if not excluded_task_ids:
                set_cached_recent_tasks(group_id, limit, result)

            return result
    except Exception as e:
        logger.error(f"[DB] fetch_recent_tasks error: {e}", exc_info=True)
        return []
    finally:
        db_operation_latency.labels(operation="fetch_recent_tasks").observe(time.time() - start)


async def save_task(task_data: dict) -> int:
    """Save a single task (one row per group message)."""
    start = time.time()
    try:
        deadline = task_data.get('deadline')
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))

        applies_at = task_data.get('applies_at')
        if isinstance(applies_at, str):
            applies_at = datetime.fromisoformat(applies_at.replace('Z', '+00:00'))

        async with pool.acquire() as conn:
            task_id = await conn.fetchval("""
                INSERT INTO tasks (
                    group_id, message_sender_id, title, action_required,
                    deadline, source_message_text, message_type,
                    applies_at, location, form_url, reminder_strategy, reminder_level
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,0)
                RETURNING id
            """,
                task_data.get('group_id'),
                task_data.get('message_sender_id'),
                task_data.get('title'),
                task_data.get('action_required'),
                deadline,
                task_data.get('source_message_text'),
                task_data.get('message_type', 'deadline'),
                applies_at,
                task_data.get('location'),
                task_data.get('form_url'),
                task_data.get('reminder_strategy', 'standard'),
            )
            logger.info(f"[DB] Task saved: {task_id}")

            from workers.text_extractor.services.redis_client import invalidate_recent_tasks_cache
            invalidate_recent_tasks_cache(task_data.get('group_id'))

            return task_id
    except Exception as e:
        logger.error(f"[DB] save_task error: {e}", exc_info=True)
        raise
    finally:
        db_operation_latency.labels(operation="save_task").observe(time.time() - start)


async def update_task_by_id(task_id: int, new_deadline=None, new_location: str = None) -> bool:
    """Update a specific task by ID."""
    if isinstance(new_deadline, str):
        new_deadline = datetime.fromisoformat(new_deadline.replace('Z', '+00:00'))

    start = time.time()
    try:
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE tasks
                SET deadline = COALESCE($1, deadline),
                    location = COALESCE($2, location),
                    updated_at = NOW()
                WHERE id = $3
            """, new_deadline, new_location, task_id)
            success = result == "UPDATE 1"
            logger.info(f"[DB] update_task_by_id {task_id}: {result}")
            return success
    except Exception as e:
        logger.error(f"[DB] update_task_by_id error: {e}", exc_info=True)
        return False
    finally:
        db_operation_latency.labels(operation="update_task_by_id").observe(time.time() - start)


async def fetch_due_tasks_with_subscribers(reminder_level: int, time_threshold: datetime) -> list:
    """
    Fetch tasks due within threshold, joined with group subscribers.
    Returns one row per (task, subscriber) pair.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
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
            WHERE t.reminder_level = $1
            AND t.deadline <= $2
            ORDER BY t.deadline ASC
        """, reminder_level, time_threshold)
        return [dict(r) for r in rows]


async def increment_reminder_level(task_id: int):
    """Increment reminder_level by 1 for a task."""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE tasks
            SET reminder_level = reminder_level + 1,
                updated_at = NOW()
            WHERE id = $1
        """, task_id)


async def search_tasks_by_title_fuzzy(group_id: int, search_title: str, limit: int = 5, excluded_task_ids: list = []) -> list:
    """Fuzzy search for tasks by title with exclusion support."""
    start_time = time.time()
    try:
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

            if excluded_task_ids:
                query = """
                    SELECT
                        id, group_id, title, action_required, deadline, created_at,
                        similarity(LOWER(title), LOWER($2)) AS similarity
                    FROM tasks
                    WHERE group_id = $1
                      AND deadline > NOW() - INTERVAL '7 days'
                      AND id != ALL($4)
                      AND similarity(LOWER(title), LOWER($2)) > 0.3
                    ORDER BY similarity DESC
                    LIMIT $3
                """
                rows = await conn.fetch(query, group_id, search_title, limit, excluded_task_ids)
            else:
                query = """
                    SELECT
                        id, group_id, title, action_required, deadline, created_at,
                        similarity(LOWER(title), LOWER($2)) AS similarity
                    FROM tasks
                    WHERE group_id = $1
                      AND deadline > NOW() - INTERVAL '7 days'
                      AND similarity(LOWER(title), LOWER($2)) > 0.3
                    ORDER BY similarity DESC
                    LIMIT $3
                """
                rows = await conn.fetch(query, group_id, search_title, limit)

            result = [dict(row) for row in rows]
            logger.info(f"[DB] Fuzzy search for '{search_title}' returned {len(result)} matches")
            return result

    except Exception as e:
        logger.error(f"[DB] Error in fuzzy search: {e}", exc_info=True)
        return []
    finally:
        db_operation_latency.labels(operation="search_tasks_by_title_fuzzy").observe(time.time() - start_time)


# Kept for group-level task redesign
# async def update_tasks_by_title_and_group(group_id: int, title: str, new_deadline) -> int:
#     """Update all tasks matching title in a group."""
#     from workers.text_extractor.services.redis_client import invalidate_recent_tasks_cache
#     from datetime import datetime
#
#     if isinstance(new_deadline, str):
#         new_deadline = datetime.fromisoformat(new_deadline.replace('Z', '+00:00'))
#
#     start = time.time()
#     try:
#         async with pool.acquire() as conn:
#             rows = await conn.fetch("""
#                 UPDATE tasks
#                 SET deadline = $1, updated_at = NOW()
#                 WHERE group_id = $2
#                 AND LOWER(title) = LOWER($3)
#                 AND deadline > NOW() - INTERVAL '7 days'
#                 RETURNING id
#             """, new_deadline, group_id, title)
#             count = len(rows)
#             if count > 0:
#                 invalidate_recent_tasks_cache(group_id)
#             return count
#     except Exception as e:
#         logger.error(f"[DB] update_tasks_by_title_and_group error: {e}", exc_info=True)
#         return 0
#     finally:
#         db_operation_latency.labels(operation="update_tasks_by_title_and_group").observe(time.time() - start)
