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
    Get tasks for multi-level reminder system.
    
    Returns tasks in 3 windows:
    - Level 0: Tasks due in < 24 hours (24-hour warning)
    - Level 1: Tasks due in < 1 hour (1-hour final call)
    - Level 2: Tasks due now (deadline alert)
    
    Returns:
        List of task dictionaries with id, user_id, title, action_required, deadline, reminder_level
    """
    if _pool is None:
        await init_pool()
    
    query = """
        -- Window 1: 24-Hour Warning
        SELECT id, user_id, title, action_required, deadline, reminder_level, '24h' as window
        FROM tasks
        WHERE deadline <= NOW() + INTERVAL '24 hours' 
        AND deadline > NOW()
        AND reminder_level = 0
        
        UNION ALL
        
        -- Window 2: 1-Hour Final Call
        SELECT id, user_id, title, action_required, deadline, reminder_level, '1h' as window
        FROM tasks
        WHERE deadline <= NOW() + INTERVAL '1 hour'
        AND deadline > NOW()
        AND reminder_level = 1
        
        UNION ALL
        
        -- Window 3: Deadline Alert
        SELECT id, user_id, title, action_required, deadline, reminder_level, 'now' as window
        FROM tasks
        WHERE deadline <= NOW()
        AND reminder_level = 2
        
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
                'deadline': row['deadline'],
                'reminder_level': row['reminder_level'],
                'window': row['window']
            })
        
        return tasks


async def update_reminder_level(task_id: int, new_level: int) -> bool:
    """
    Update the reminder_level for a task.
    
    Args:
        task_id: The task ID to update
        new_level: The new reminder level (1, 2, or 3)
        
    Returns:
        True if successful, False otherwise
    """
    if _pool is None:
        await init_pool()
    
    query = """
        UPDATE tasks 
        SET reminder_level = $2
        WHERE id = $1
    """
    
    try:
        async with _pool.acquire() as conn:
            await conn.execute(query, task_id, new_level)
        return True
    except Exception as e:
        print(f"Error updating reminder_level for task {task_id}: {e}")
        return False
