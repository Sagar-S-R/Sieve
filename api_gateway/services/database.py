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



async def subscribe_to_group(group_id: int, subscriber_id: int) -> bool:
    """
    Subscribe a user to a group's reminders.
    
    Args:
        group_id: The Telegram group ID
        subscriber_id: The user ID to subscribe
        
    Returns:
        True if subscribed (new or existing), False on error
    """
    from api_gateway.services.redis_client import (
        invalidate_subscribers_cache,
        invalidate_user_subs_cache
    )
    
    pool = await get_pool()
    
    query = """
        INSERT INTO group_subscriptions (group_id, subscriber_id)
        VALUES ($1, $2)
        ON CONFLICT (group_id, subscriber_id) DO NOTHING
        RETURNING id
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, group_id, subscriber_id)
            
            # Invalidate caches
            await invalidate_subscribers_cache(group_id)
            await invalidate_user_subs_cache(subscriber_id)
            
            return True  # Success (new or already exists)
    except Exception as e:
        print(f"[DB] Error subscribing user {subscriber_id} to group {group_id}: {e}")
        return False


async def unsubscribe_from_group(group_id: int, subscriber_id: int) -> bool:
    """
    Unsubscribe a user from a group's reminders.
    
    Args:
        group_id: The Telegram group ID
        subscriber_id: The user ID to unsubscribe
        
    Returns:
        True if unsubscribed, False if wasn't subscribed
    """
    from api_gateway.services.redis_client import (
        invalidate_subscribers_cache,
        invalidate_user_subs_cache
    )
    
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
                # Invalidate caches
                await invalidate_subscribers_cache(group_id)
                await invalidate_user_subs_cache(subscriber_id)
            
            return result is not None
    except Exception as e:
        print(f"[DB] Error unsubscribing user {subscriber_id} from group {group_id}: {e}")
        return False


async def get_group_subscribers(group_id: int) -> list:
    """
    Get all subscribers for a group with caching.
    
    Args:
        group_id: The Telegram group ID
        
    Returns:
        List of subscriber IDs
    """
    from api_gateway.services.redis_client import (
        get_cached_subscribers,
        set_cached_subscribers
    )
    
    # Try cache first
    cached = await get_cached_subscribers(group_id)
    if cached is not None:
        print(f"[CACHE HIT] subscribers:{group_id} ({len(cached)} subscribers)")
        return cached
    
    # Cache miss - query database
    print(f"[CACHE MISS] subscribers:{group_id}")
    pool = await get_pool()
    
    query = """
        SELECT subscriber_id
        FROM group_subscriptions
        WHERE group_id = $1
        ORDER BY subscribed_at ASC
    """
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, group_id)
            subscribers = [row['subscriber_id'] for row in rows]
            print(f"[DB] Fetched {len(subscribers)} subscribers for group {group_id}")
            
            # Store in cache
            await set_cached_subscribers(group_id, subscribers)
            
            return subscribers
    except Exception as e:
        print(f"[DB] Error fetching subscribers for group {group_id}: {e}")
        return []



async def get_user_subscriptions(user_id: int) -> list:
    """
    Get all groups the user is subscribed to with caching.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        List of dicts with group_id, subscribed_at
    """
    from api_gateway.services.redis_client import (
        get_cached_user_subs,
        set_cached_user_subs
    )
    
    # Try cache first
    cached = await get_cached_user_subs(user_id)
    if cached is not None:
        print(f"[CACHE HIT] user_subs:{user_id} ({len(cached)} subscriptions)")
        return cached
    
    # Cache miss - query database
    print(f"[CACHE MISS] user_subs:{user_id}")
    pool = await get_pool()
    
    query = """
        SELECT group_id, subscribed_at
        FROM group_subscriptions
        WHERE subscriber_id = $1
        ORDER BY subscribed_at DESC
    """
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            subs = [
                {
                    'group_id': row['group_id'],
                    'subscribed_at': row['subscribed_at']
                }
                for row in rows
            ]
            print(f"[DB] Fetched {len(subs)} subscriptions for user {user_id}")
            
            # Store in cache
            await set_cached_user_subs(user_id, subs)
            
            return subs
    except Exception as e:
        print(f"[DB] Error fetching subscriptions for user {user_id}: {e}")
        return []


async def get_user_tasks(user_id: int) -> dict:
    """
    Get all tasks for a user, grouped by status.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        {
            'upcoming': [...],  # deadline > now
            'overdue': [...]    # deadline < now
        }
    """
    from datetime import datetime, timezone
    
    pool = await get_pool()
    
    query = """
        SELECT id, user_id, group_id, title, action_required, deadline, created_at
        FROM tasks
        WHERE user_id = $1
        ORDER BY deadline ASC
    """
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            
            now = datetime.now(timezone.utc)
            upcoming = []
            overdue = []
            
            for row in rows:
                task = dict(row)
                if task['deadline'] > now:
                    upcoming.append(task)
                else:
                    overdue.append(task)
            
            return {
                'upcoming': upcoming,
                'overdue': overdue
            }
    except Exception as e:
        print(f"[DB] Error fetching tasks for user {user_id}: {e}")
        return {'upcoming': [], 'overdue': []}


async def get_task_by_id(task_id: int) -> Optional[dict]:
    """
    Get task details by ID.
    
    Args:
        task_id: Task ID
        
    Returns:
        Task dict if found, None otherwise
    """
    pool = await get_pool()
    
    query = """
        SELECT id, user_id, group_id, title, action_required, deadline, created_at
        FROM tasks
        WHERE id = $1
    """
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id)
            return dict(row) if row else None
    except Exception as e:
        print(f"[DB] Error fetching task {task_id}: {e}")
        return None


async def delete_task(task_id: int, user_id: int) -> Optional[dict]:
    """
    Delete a task (with ownership check).
    
    Args:
        task_id: Task ID
        user_id: User ID (for ownership check)
        
    Returns:
        Deleted task details if successful, None otherwise
    """
    from api_gateway.services.redis_client import invalidate_recent_tasks_cache_async
    
    pool = await get_pool()
    
    query = """
        DELETE FROM tasks
        WHERE id = $1 AND user_id = $2
        RETURNING id, title, deadline, group_id
    """
    
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, task_id, user_id)
            
            if row:
                task = dict(row)
                # Invalidate cache for this group
                await invalidate_recent_tasks_cache_async(task['group_id'])
                print(f"[DB] Deleted task {task_id} for user {user_id}")
                return task
            
            return None
    except Exception as e:
        print(f"[DB] Error deleting task {task_id}: {e}")
        return None


async def update_task_deadline(task_id: int, user_id: int, new_deadline, group_id: int) -> bool:
    """
    Update task deadline (with ownership check).
    
    Args:
        task_id: Task ID
        user_id: User ID (for ownership check)
        new_deadline: New deadline (UTC datetime)
        group_id: Group ID (for cache invalidation)
        
    Returns:
        True if updated, False otherwise
    """
    from api_gateway.services.redis_client import invalidate_recent_tasks_cache_async
    from datetime import datetime
    
    pool = await get_pool()
    
    # Parse deadline if string
    if isinstance(new_deadline, str):
        new_deadline = datetime.fromisoformat(new_deadline.replace('Z', '+00:00'))
    
    query = """
        UPDATE tasks
        SET deadline = $1, updated_at = NOW()
        WHERE id = $2 AND user_id = $3
        RETURNING id
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, new_deadline, task_id, user_id)
            
            if result:
                # Invalidate cache for this group
                await invalidate_recent_tasks_cache_async(group_id)
                print(f"[DB] Updated task {task_id} deadline for user {user_id}")
                return True
            
            return False
    except Exception as e:
        print(f"[DB] Error updating task {task_id}: {e}")
        return False
