import redis.asyncio as redis
import json
from typing import Optional
from api_gateway.core.config import settings

# Redis client singleton
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def get_hitl_lock(user_id: int) -> Optional[dict]:
    """
    Check if HITL lock exists for user.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Saved state dict if lock exists, None otherwise
    """
    client = await get_redis_client()
    key = f"awaiting_clarification:{user_id}"
    
    data = await client.get(key)
    if data:
        return json.loads(data)
    return None


# ============================================================================
# CACHING FUNCTIONS
# ============================================================================

async def get_cached_subscribers(group_id: int) -> Optional[list]:
    """
    Get subscriber list from cache (async).
    
    Args:
        group_id: The Telegram group ID
        
    Returns:
        List of subscriber IDs if cached, None on cache miss or error
    """
    try:
        client = await get_redis_client()
        key = f"cache:subscribers:{group_id}"
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"[CACHE ERROR] Failed to get subscribers:{group_id}: {e}")
        return None


async def set_cached_subscribers(group_id: int, subscribers: list, ttl_seconds: int = 600):
    """
    Store subscriber list in cache (async).
    
    Args:
        group_id: The Telegram group ID
        subscribers: List of subscriber IDs
        ttl_seconds: Time to live (default 10 minutes)
    """
    try:
        client = await get_redis_client()
        key = f"cache:subscribers:{group_id}"
        await client.setex(key, ttl_seconds, json.dumps(subscribers))
    except Exception as e:
        print(f"[CACHE ERROR] Failed to cache subscribers:{group_id}: {e}")


async def get_cached_user_subs(user_id: int) -> Optional[list]:
    """
    Get user subscriptions from cache (async).
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        List of subscription dicts if cached, None on cache miss or error
    """
    try:
        client = await get_redis_client()
        key = f"cache:user_subs:{user_id}"
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"[CACHE ERROR] Failed to get user_subs:{user_id}: {e}")
        return None


async def set_cached_user_subs(user_id: int, subs: list, ttl_seconds: int = 600):
    """
    Store user subscriptions in cache (async).
    
    Args:
        user_id: The Telegram user ID
        subs: List of subscription dicts
        ttl_seconds: Time to live (default 10 minutes)
    """
    try:
        client = await get_redis_client()
        key = f"cache:user_subs:{user_id}"
        # Convert datetime objects to ISO strings for JSON serialization
        serializable_subs = []
        for sub in subs:
            sub_copy = dict(sub)
            for key_name, value in sub_copy.items():
                if hasattr(value, 'isoformat'):
                    sub_copy[key_name] = value.isoformat()
            serializable_subs.append(sub_copy)
        
        await client.setex(key, ttl_seconds, json.dumps(serializable_subs))
    except Exception as e:
        print(f"[CACHE ERROR] Failed to cache user_subs:{user_id}: {e}")


async def invalidate_subscribers_cache(group_id: int):
    """
    Invalidate (delete) subscriber cache for a group (async).
    
    Args:
        group_id: The Telegram group ID
    """
    try:
        client = await get_redis_client()
        key = f"cache:subscribers:{group_id}"
        await client.delete(key)
        print(f"[CACHE INVALIDATE] subscribers:{group_id}")
    except Exception as e:
        print(f"[CACHE ERROR] Failed to invalidate subscribers:{group_id}: {e}")


async def invalidate_user_subs_cache(user_id: int):
    """
    Invalidate (delete) user subscriptions cache (async).
    
    Args:
        user_id: The Telegram user ID
    """
    try:
        client = await get_redis_client()
        key = f"cache:user_subs:{user_id}"
        await client.delete(key)
        print(f"[CACHE INVALIDATE] user_subs:{user_id}")
    except Exception as e:
        print(f"[CACHE ERROR] Failed to invalidate user_subs:{user_id}: {e}")


# ============================================================================
# EDIT STATE MANAGEMENT
# ============================================================================

async def set_edit_task_state(user_id: int, task_data: dict, ttl_seconds: int = 300):
    """
    Store edit task state for user.
    
    Args:
        user_id: Telegram user ID
        task_data: Dict with task_id, task_title, current_deadline, group_id
        ttl_seconds: Time to live (default 5 minutes)
    """
    try:
        client = await get_redis_client()
        key = f"edit_task:{user_id}"
        await client.setex(key, ttl_seconds, json.dumps(task_data))
        print(f"[REDIS] Set edit state for user {user_id}")
    except Exception as e:
        print(f"[REDIS ERROR] Failed to set edit state for user {user_id}: {e}")


async def get_edit_task_state(user_id: int) -> Optional[dict]:
    """
    Get edit task state for user.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Task data dict if in edit mode, None otherwise
    """
    try:
        client = await get_redis_client()
        key = f"edit_task:{user_id}"
        data = await client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        print(f"[REDIS ERROR] Failed to get edit state for user {user_id}: {e}")
        return None


async def clear_edit_task_state(user_id: int):
    """
    Clear edit task state for user.
    
    Args:
        user_id: Telegram user ID
    """
    try:
        client = await get_redis_client()
        key = f"edit_task:{user_id}"
        await client.delete(key)
        print(f"[REDIS] Cleared edit state for user {user_id}")
    except Exception as e:
        print(f"[REDIS ERROR] Failed to clear edit state for user {user_id}: {e}")


async def invalidate_recent_tasks_cache_async(group_id: int):
    """
    Invalidate recent_tasks cache for a group (async version).
    
    Args:
        group_id: The Telegram group ID
    """
    try:
        client = await get_redis_client()
        pattern = f"cache:recent_tasks:{group_id}:*"
        
        # Scan for keys matching pattern
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await client.delete(*keys)
            print(f"[CACHE INVALIDATE] recent_tasks:{group_id}:* ({len(keys)} keys)")
    except Exception as e:
        print(f"[CACHE ERROR] Failed to invalidate recent_tasks:{group_id}: {e}")


# ============================================================================
# ROLLING MESSAGE BUFFER (NEW)
# ============================================================================

async def push_raw_message(group_id: int, message_data: dict, window_size: int = 20, ttl_seconds: int = 7200):
    """
    Push raw message to rolling window BEFORE triage.
    Keeps last window_size messages per group.
    TTL: 2 hours.
    Key: raw_msgs:{group_id}
    
    Args:
        group_id: Telegram group ID
        message_data: Dict with user_id, message_text, timestamp, message_id
        window_size: Max messages to keep (default 20)
        ttl_seconds: Expiry time (default 2 hours)
    """
    import json
    try:
        client = await get_redis_client()
        key = f"raw_msgs:{group_id}"
        
        # Add to left (newest first)
        await client.lpush(key, json.dumps(message_data))
        # Trim to keep only last N messages
        await client.ltrim(key, 0, window_size - 1)
        # Set expiry
        await client.expire(key, ttl_seconds)
    except Exception as e:
        print(f"[BUFFER ERROR] Failed to push message to buffer:{group_id}: {e}")


async def get_raw_message_window(group_id: int, limit: int = 20) -> list:
    """
    Get recent raw messages for a group.
    Used by context_node to build conversation window.
    
    Args:
        group_id: Telegram group ID
        limit: Number of messages to retrieve
        
    Returns:
        List of message dicts, most recent first
    """
    import json
    try:
        client = await get_redis_client()
        key = f"raw_msgs:{group_id}"
        # Get last N messages
        messages_json = await client.lrange(key, 0, limit - 1)
        return [json.loads(msg) for msg in messages_json]
    except Exception as e:
        print(f"[BUFFER ERROR] Failed to get buffer:{group_id}: {e}")
        return []


