import redis
import json
from workers.media_extractor.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)


def set_hitl_lock(user_id: int, state_data: dict, ttl_seconds: int = 3600):
    """Save HITL state to Redis with TTL."""
    key = f"awaiting_clarification:{user_id}"
    redis_client.setex(key, ttl_seconds, json.dumps(state_data))


def check_hitl_lock(user_id: int) -> dict | None:
    """Check if HITL lock exists for user."""
    key = f"awaiting_clarification:{user_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None


def clear_hitl_lock(user_id: int):
    """Clear HITL lock for user."""
    key = f"awaiting_clarification:{user_id}"
    redis_client.delete(key)
