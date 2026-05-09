"""Database service with asyncpg implementation."""
import time
import asyncpg
from workers.text_extractor.core.config import settings
from workers.text_extractor.core.metrics import db_operation_latency
from workers.text_extractor.core.logger import logger


async def get_db_connection():
    """Get database connection."""
    return await asyncpg.connect(settings.DATABASE_URL)


async def fetch_recent_tasks(group_id: int, limit: int = 10):
    """Fetch recent tasks from database."""
    start_time = time.time()
    try:
        conn = await get_db_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT id, user_id, group_id, title, action_required, deadline, created_at
                FROM tasks
                WHERE group_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                group_id,
                limit
            )
            result = [dict(row) for row in rows]
            logger.info(f"[DB] Fetched {len(result)} recent tasks for group {group_id}")
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"[DB] Error fetching tasks: {e}", exc_info=True)
        return []
    finally:
        duration = time.time() - start_time
        db_operation_latency.labels(operation="fetch_recent_tasks").observe(duration)


async def save_task(task_data: dict):
    """Save task to database."""
    start_time = time.time()
    try:
        conn = await get_db_connection()
        try:
            # Parse deadline string to datetime if it's a string
            deadline = task_data.get('deadline')
            if isinstance(deadline, str):
                from datetime import datetime
                # Parse ISO 8601 format
                deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            
            task_id = await conn.fetchval(
                """
                INSERT INTO tasks (user_id, group_id, title, action_required, deadline, is_sent)
                VALUES ($1, $2, $3, $4, $5, false)
                RETURNING id
                """,
                task_data.get('user_id'),
                task_data.get('group_id'),
                task_data.get('title'),
                task_data.get('action_required'),
                deadline
            )
            logger.info(f"[DB] Task saved with ID: {task_id}")
            return task_id
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"[DB] Error saving task: {e}", exc_info=True)
        raise
    finally:
        duration = time.time() - start_time
        db_operation_latency.labels(operation="save_task").observe(duration)
