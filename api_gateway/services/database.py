import asyncpg
from typing import Optional
from api_gateway.core.config import settings

# Connection pool singleton
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return _pool


async def save_completed_task(task_data: dict) -> int:
    """
    Save a completed task to the database after HITL resolution.
    
    Args:
        task_data: Dictionary with user_id, group_id, title, action_required, deadline
        
    Returns:
        Task ID of inserted task
    """
    pool = await get_pool()
    
    query = """
        INSERT INTO tasks (user_id, group_id, title, action_required, deadline)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """
    
    async with pool.acquire() as conn:
        task_id = await conn.fetchval(
            query,
            task_data.get('user_id'),
            task_data.get('group_id'),
            task_data.get('title'),
            task_data.get('action_required'),
            task_data.get('deadline')
        )
    
    return task_id
