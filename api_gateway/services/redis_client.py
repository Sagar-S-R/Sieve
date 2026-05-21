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


async def delete_hitl_lock(user_id: int) -> bool:
    """
    Delete HITL lock for user.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if deleted, False otherwise
    """
    client = await get_redis_client()
    key = f"awaiting_clarification:{user_id}"
    
    result = await client.delete(key)
    return result > 0


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
