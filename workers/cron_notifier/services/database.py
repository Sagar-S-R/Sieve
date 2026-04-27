import asyncpg
from typing import List, Dict, Any, Optional
from workers.cron_notifier.core.config import settings

# Connection pool singleton
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


async def get_due_tasks() -> List[Dict[str, Any]]:
    """
    Get all tasks where deadline has arrived and not yet sent.
    
    Returns:
        List of task dictionaries with id, user_id, title, action_required
    """
    if _pool is None:
        await init_pool()
    
    query = """
        SELECT id, user_id, title, action_required, deadline
        FROM tasks
        WHERE deadline <= NOW() 
        AND is_sent = FALSE
        ORDER BY deadline ASC
    """
    
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query)
        
        tasks = []
        for row in rows:
            tasks.append({
                'id': row['id'],
                'user_id': row['user_id'],
                'title': row['title'],
                'action_required': row['action_required'],
                'deadline': row['deadline']
            })
        
        return tasks


async def mark_task_sent(task_id: int) -> bool:
    """
    Mark a task as sent in the database.
    
    Args:
        task_id: The task ID to mark as sent
        
    Returns:
        True if successful, False otherwise
    """
    if _pool is None:
        await init_pool()
    
    query = """
        UPDATE tasks 
        SET is_sent = TRUE 
        WHERE id = $1
    """
    
    try:
        async with _pool.acquire() as conn:
            await conn.execute(query, task_id)
        return True
    except Exception as e:
        print(f"Error marking task {task_id} as sent: {e}")
        return False
