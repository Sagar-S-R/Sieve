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


async def subscribe_to_group(group_id: int, subscriber_id: int) -> bool:
    """
    Subscribe a user to a group's reminders.
    
    Args:
        group_id: The Telegram group ID
        subscriber_id: The user ID to subscribe
        
    Returns:
        True if subscribed (new or existing), False on error
    """
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
    pool = await get_pool()
    
    query = """
        DELETE FROM group_subscriptions
        WHERE group_id = $1 AND subscriber_id = $2
        RETURNING id
    """
    
    try:
        async with pool.acquire() as conn:
            result = await conn.fetchval(query, group_id, subscriber_id)
            return result is not None
    except Exception as e:
        print(f"[DB] Error unsubscribing user {subscriber_id} from group {group_id}: {e}")
        return False


async def get_group_subscribers(group_id: int) -> list:
    """
    Get all subscribers for a group.
    
    Args:
        group_id: The Telegram group ID
        
    Returns:
        List of subscriber IDs
    """
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
            return [row['subscriber_id'] for row in rows]
    except Exception as e:
        print(f"[DB] Error fetching subscribers for group {group_id}: {e}")
        return []


async def get_user_available_groups(user_id: int) -> list:
    """
    Get all groups where the bot is present and the user is a member.
    Shows subscription status for each group.
    
    Note: This is a simplified version. In production, you'd need to track
    group membership separately or use Telegram API to check.
    
    For now, we'll return groups where:
    - Bot has been added (exists in group_subscriptions)
    - Show if user is subscribed or not
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        List of dicts with group_id, group_name, is_subscribed
    """
    pool = await get_pool()
    
    # Get all groups where bot is present (has at least one subscriber)
    # and check if this user is subscribed
    query = """
        SELECT DISTINCT 
            gs.group_id,
            CASE WHEN user_sub.subscriber_id IS NOT NULL THEN true ELSE false END as is_subscribed
        FROM group_subscriptions gs
        LEFT JOIN group_subscriptions user_sub 
            ON user_sub.group_id = gs.group_id 
            AND user_sub.subscriber_id = $1
        ORDER BY gs.group_id
    """
    
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            return [
                {
                    'group_id': row['group_id'],
                    'group_name': None,  # We don't store group names yet
                    'is_subscribed': row['is_subscribed']
                }
                for row in rows
            ]
    except Exception as e:
        print(f"[DB] Error fetching available groups for user {user_id}: {e}")
        return []


async def get_user_subscriptions(user_id: int) -> list:
    """
    Get all groups the user is subscribed to.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        List of dicts with group_id, subscribed_at
    """
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
            return [
                {
                    'group_id': row['group_id'],
                    'subscribed_at': row['subscribed_at']
                }
                for row in rows
            ]
    except Exception as e:
        print(f"[DB] Error fetching subscriptions for user {user_id}: {e}")
        return []
