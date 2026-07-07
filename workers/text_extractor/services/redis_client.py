import redis
import json
from workers.text_extractor.core.config import settings
from pydantic import BaseModel

redis_client = redis.from_url(settings.REDIS_URL)

def serialize_state(state_data: dict) -> str:
    """Serialize state data, converting Pydantic models to dicts."""
    serializable_state = {}
    for key, value in state_data.items():
        if isinstance(value, BaseModel):
            # Convert Pydantic model to dict
            serializable_state[key] = value.model_dump()
        else:
            serializable_state[key] = value
    return json.dumps(serializable_state)

def set_hitl_lock(user_id: int, state_data: dict, ttl_seconds: int = 3600):
    key = f"awaiting_clarification:{user_id}"
    redis_client.setex(key, ttl_seconds, serialize_state(state_data))

def check_hitl_lock(user_id: int) -> dict | None:
    key = f"awaiting_clarification:{user_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None
    
def clear_hitl_lock(user_id: int):
    key = f"awaiting_clarification:{user_id}"
    redis_client.delete(key)


def is_message_processed(message_id: int, group_id: int) -> bool:
    """
    Check if a message has already been processed (idempotency check).
    
    Args:
        message_id: Telegram message ID
        group_id: Group ID where message was sent
        
    Returns:
        True if already processed, False otherwise
    """
    key = f"processed:{group_id}:{message_id}"
    return redis_client.exists(key) > 0


def mark_message_processed(message_id: int, group_id: int, ttl_seconds: int = 3600):
    """
    Mark a message as processed to prevent duplicate processing.
    
    Args:
        message_id: Telegram message ID
        group_id: Group ID where message was sent
        ttl_seconds: Time to live (default 1 hour)
    """
    key = f"processed:{group_id}:{message_id}"
    redis_client.setex(key, ttl_seconds, "1")


# ============================================================================
# CACHING FUNCTIONS
# ============================================================================

def get_cached_subscribers(group_id: int) -> list | None:
    """
    Get subscriber list from cache.
    
    Args:
        group_id: The Telegram group ID
        
    Returns:
        List of subscriber IDs if cached, None on cache miss or error
    """
    try:
        key = f"cache:subscribers:{group_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed for subscribers:{group_id}: {e}")
        return None
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"[CACHE ERROR] Deserialization failed for subscribers:{group_id}: {e}")
        return None


def set_cached_subscribers(group_id: int, subscribers: list, ttl_seconds: int = 600):
    """
    Store subscriber list in cache.
    
    Args:
        group_id: The Telegram group ID
        subscribers: List of subscriber IDs
        ttl_seconds: Time to live (default 10 minutes)
    """
    try:
        key = f"cache:subscribers:{group_id}"
        redis_client.setex(key, ttl_seconds, json.dumps(subscribers))
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed when caching subscribers:{group_id}: {e}")
    except (TypeError, ValueError) as e:
        print(f"[CACHE ERROR] Serialization failed for subscribers:{group_id}: {e}")


def get_cached_recent_tasks(group_id: int, limit: int = 10) -> list | None:
    """
    Get recent tasks from cache.
    
    Args:
        group_id: The Telegram group ID
        limit: Number of tasks to retrieve
        
    Returns:
        List of task dicts if cached, None on cache miss or error
    """
    try:
        key = f"cache:recent_tasks:{group_id}:{limit}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed for recent_tasks:{group_id}:{limit}: {e}")
        return None
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        print(f"[CACHE ERROR] Deserialization failed for recent_tasks:{group_id}:{limit}: {e}")
        return None


def set_cached_recent_tasks(group_id: int, limit: int, tasks: list, ttl_seconds: int = 300):
    """
    Store recent tasks in cache.
    
    Args:
        group_id: The Telegram group ID
        limit: Number of tasks
        tasks: List of task dicts
        ttl_seconds: Time to live (default 5 minutes)
    """
    try:
        key = f"cache:recent_tasks:{group_id}:{limit}"
        # Convert datetime objects to ISO strings for JSON serialization
        serializable_tasks = []
        for task in tasks:
            task_copy = dict(task)
            for key_name, value in task_copy.items():
                if hasattr(value, 'isoformat'):
                    task_copy[key_name] = value.isoformat()
            serializable_tasks.append(task_copy)
        
        redis_client.setex(key, ttl_seconds, json.dumps(serializable_tasks))
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed when caching recent_tasks:{group_id}:{limit}: {e}")
    except (TypeError, ValueError) as e:
        print(f"[CACHE ERROR] Serialization failed for recent_tasks:{group_id}:{limit}: {e}")


def invalidate_subscribers_cache(group_id: int):
    """
    Invalidate (delete) subscriber cache for a group.
    
    Args:
        group_id: The Telegram group ID
    """
    try:
        key = f"cache:subscribers:{group_id}"
        redis_client.delete(key)
        print(f"[CACHE INVALIDATE] subscribers:{group_id}")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed when invalidating subscribers:{group_id}: {e}")


def invalidate_recent_tasks_cache(group_id: int):
    """
    Invalidate (delete) all recent_tasks cache keys for a group.
    Uses pattern matching to delete all limits.
    
    Args:
        group_id: The Telegram group ID
    """
    try:
        pattern = f"cache:recent_tasks:{group_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            print(f"[CACHE INVALIDATE] recent_tasks:{group_id}:* ({len(keys)} keys)")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed when invalidating recent_tasks:{group_id}: {e}")


def invalidate_user_subs_cache(user_id: int):
    """
    Invalidate (delete) user subscriptions cache.
    
    Args:
        user_id: The Telegram user ID
    """
    try:
        key = f"cache:user_subs:{user_id}"
        redis_client.delete(key)
        print(f"[CACHE INVALIDATE] user_subs:{user_id}")
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[CACHE ERROR] Redis connection failed when invalidating user_subs:{user_id}: {e}")


# ============================================================================
# ROLLING MESSAGE BUFFER (NEW)
# ============================================================================

def add_message_to_buffer(group_id: int, message_text: str, max_size: int = 20):
    """
    Add a message to the rolling buffer for a group.
    Maintains last N messages in a Redis list.
    
    Args:
        group_id: The Telegram group ID
        message_text: The message text to add
        max_size: Maximum number of messages to keep (default 20)
    """
    try:
        key = f"raw_msgs:{group_id}"
        # Add to right (most recent)
        redis_client.rpush(key, message_text)
        # Trim to keep only last max_size messages
        redis_client.ltrim(key, -max_size, -1)
        # Set expiry (2 hours)
        redis_client.expire(key, 7200)
    except (redis.ConnectionError, redis.TimeoutError) as e:
        print(f"[BUFFER ERROR] Redis connection failed when adding message to buffer:{group_id}: {e}")


def get_raw_message_window(group_id: int, limit: int = 20) -> list:
    """
    Get the most recent messages from the rolling buffer.
    API Gateway uses lpush, so index 0 is the newest message.

    Args:
        group_id: The Telegram group ID
        limit: Number of messages to retrieve (default 20)

    Returns:
        List of parsed message dicts, most recent first.
    """
    key = f"raw_msgs:{group_id}"
    # lpush means index 0 is newest — read 0 to limit-1 for most recent
    raw = redis_client.lrange(key, 0, limit - 1)
    messages = []
    for item in raw:
        try:
            messages.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            continue
    return messages

