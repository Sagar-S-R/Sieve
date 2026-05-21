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
    """Fetch recent tasks from database with caching."""
    from workers.text_extractor.services.redis_client import (
        get_cached_recent_tasks,
        set_cached_recent_tasks
    )
    
    # Try cache first
    cached = get_cached_recent_tasks(group_id, limit)
    if cached is not None:
        logger.info(f"[CACHE HIT] recent_tasks:{group_id}:{limit} ({len(cached)} tasks)")
        return cached
    
    # Cache miss - query database
    logger.info(f"[CACHE MISS] recent_tasks:{group_id}:{limit}")
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
            
            # Store in cache
            set_cached_recent_tasks(group_id, limit, result)
            
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
                INSERT INTO tasks (user_id, group_id, message_sender_id, title, action_required, deadline, reminder_level)
                VALUES ($1, $2, $3, $4, $5, $6, 0)
                RETURNING id
                """,
                task_data.get('user_id'),
                task_data.get('group_id'),
                task_data.get('message_sender_id'),
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


async def get_group_subscribers(group_id: int) -> list:
    """
    Get all subscribers for a group with caching.
    
    Args:
        group_id: The Telegram group ID
        
    Returns:
        List of subscriber IDs
    """
    from workers.text_extractor.services.redis_client import (
        get_cached_subscribers,
        set_cached_subscribers
    )
    
    # Try cache first
    cached = get_cached_subscribers(group_id)
    if cached is not None:
        logger.info(f"[CACHE HIT] subscribers:{group_id} ({len(cached)} subscribers)")
        return cached
    
    # Cache miss - query database
    logger.info(f"[CACHE MISS] subscribers:{group_id}")
    try:
        conn = await get_db_connection()
        try:
            rows = await conn.fetch(
                """
                SELECT subscriber_id
                FROM group_subscriptions
                WHERE group_id = $1
                ORDER BY subscribed_at ASC
                """,
                group_id
            )
            subscribers = [row['subscriber_id'] for row in rows]
            logger.info(f"[DB] Fetched {len(subscribers)} subscribers for group {group_id}")
            
            # Store in cache
            set_cached_subscribers(group_id, subscribers)
            
            return subscribers
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"[DB] Error fetching subscribers for group {group_id}: {e}", exc_info=True)
        return []


async def save_tasks_atomic(subscribers: list, group_id: int, message_sender_id: int, 
                            title: str, action_required: str, deadline):
    """
    Save tasks for all subscribers atomically (all-or-nothing).
    
    Args:
        subscribers: List of subscriber IDs
        group_id: Group ID
        message_sender_id: Who sent the original message
        title: Task title
        action_required: Task action
        deadline: Task deadline
        
    Returns:
        List of created task IDs
    """
    from workers.text_extractor.services.redis_client import invalidate_recent_tasks_cache
    
    start_time = time.time()
    try:
        conn = await get_db_connection()
        try:
            # Parse deadline if string
            if isinstance(deadline, str):
                from datetime import datetime
                deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            
            task_ids = []
            
            # CRITICAL: Use transaction for atomic operation
            async with conn.transaction():
                for subscriber_id in subscribers:
                    task_id = await conn.fetchval(
                        """
                        INSERT INTO tasks (user_id, group_id, message_sender_id, title, action_required, deadline, reminder_level)
                        VALUES ($1, $2, $3, $4, $5, $6, 0)
                        RETURNING id
                        """,
                        subscriber_id,
                        group_id,
                        message_sender_id,
                        title,
                        action_required,
                        deadline
                    )
                    task_ids.append(task_id)
                    logger.info(f"[DB] Task {task_id} saved for subscriber {subscriber_id}")
            
            logger.info(f"[DB] Transaction complete: {len(task_ids)} tasks created")
            
            # Invalidate recent_tasks cache after successful save
            invalidate_recent_tasks_cache(group_id)
            
            return task_ids
            
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"[DB] Transaction failed, rolling back: {e}", exc_info=True)
        raise
    finally:
        duration = time.time() - start_time
        db_operation_latency.labels(operation="save_tasks_atomic").observe(duration)
