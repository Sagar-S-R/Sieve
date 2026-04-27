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
