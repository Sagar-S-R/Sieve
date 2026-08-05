import os
import json
import redis.asyncio as redis
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# Redis Client Singleton (Connection pool initialized lazily on first command)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def serialize_state(state_data: dict) -> str:
    """Serialize state data, converting Pydantic models and datetimes to dicts/strings."""
    serializable_state = {}
    for key, value in state_data.items():
        if isinstance(value, BaseModel):
            serializable_state[key] = value.model_dump()
        elif hasattr(value, 'isoformat'):
            serializable_state[key] = value.isoformat()
        else:
            serializable_state[key] = value
    return json.dumps(serializable_state)


# ============================================================================
# HITL LOCKS
# ============================================================================

async def set_hitl_lock(user_id: int, state_data: dict, ttl_seconds: int = 3600):
    key = f"awaiting_clarification:{user_id}"
    await redis_client.setex(key, ttl_seconds, serialize_state(state_data))

async def check_hitl_lock(user_id: int) -> Optional[dict]:
    key = f"awaiting_clarification:{user_id}"
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None

async def clear_hitl_lock(user_id: int):
    key = f"awaiting_clarification:{user_id}"
    await redis_client.delete(key)

async def set_group_hitl_lock(group_id: int, state_data: dict, ttl_seconds: int = 3600):
    """One HITL lock per group. First valid reply in the group resolves it."""
    key = f"awaiting_clarification:group:{group_id}"
    await redis_client.setex(key, ttl_seconds, serialize_state(state_data))

async def check_group_hitl_lock(group_id: int) -> Optional[dict]:
    key = f"awaiting_clarification:group:{group_id}"
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None

async def clear_group_hitl_lock(group_id: int):
    key = f"awaiting_clarification:group:{group_id}"
    await redis_client.delete(key)


# ============================================================================
# IDEMPOTENCY (DUPLICATE MESSAGE PREVENTION)
# ============================================================================

async def is_message_processed(message_id: int, group_id: int) -> bool:
    key = f"processed:{group_id}:{message_id}"
    return await redis_client.exists(key) > 0

async def mark_message_processed(message_id: int, group_id: int, ttl_seconds: int = 3600):
    key = f"processed:{group_id}:{message_id}"
    await redis_client.setex(key, ttl_seconds, "1")


# ============================================================================
# CACHING FUNCTIONS
# ============================================================================

async def get_cached_subscribers(group_id: int) -> Optional[list]:
    try:
        key = f"cache:subscribers:{group_id}"
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to get subscribers:{group_id}: {e}")
        return None

async def set_cached_subscribers(group_id: int, subscribers: list, ttl_seconds: int = 600):
    try:
        key = f"cache:subscribers:{group_id}"
        await redis_client.setex(key, ttl_seconds, json.dumps(subscribers))
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to cache subscribers:{group_id}: {e}")

async def invalidate_subscribers_cache(group_id: int):
    try:
        key = f"cache:subscribers:{group_id}"
        await redis_client.delete(key)
        logger.info(f"[CACHE INVALIDATE] subscribers:{group_id}")
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to invalidate subscribers:{group_id}: {e}")


async def get_cached_user_subs(user_id: int) -> Optional[list]:
    try:
        key = f"cache:user_subs:{user_id}"
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to get user_subs:{user_id}: {e}")
        return None

async def set_cached_user_subs(user_id: int, subs: list, ttl_seconds: int = 600):
    try:
        key = f"cache:user_subs:{user_id}"
        serializable_subs = []
        for sub in subs:
            sub_copy = dict(sub)
            for key_name, value in sub_copy.items():
                if hasattr(value, 'isoformat'):
                    sub_copy[key_name] = value.isoformat()
            serializable_subs.append(sub_copy)
        await redis_client.setex(key, ttl_seconds, json.dumps(serializable_subs))
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to cache user_subs:{user_id}: {e}")

async def invalidate_user_subs_cache(user_id: int):
    try:
        key = f"cache:user_subs:{user_id}"
        await redis_client.delete(key)
        logger.info(f"[CACHE INVALIDATE] user_subs:{user_id}")
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to invalidate user_subs:{user_id}: {e}")


async def get_cached_recent_tasks(group_id: int, limit: int = 10) -> Optional[list]:
    try:
        key = f"cache:recent_tasks:{group_id}:{limit}"
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed for recent_tasks:{group_id}:{limit}: {e}")
        return None

async def set_cached_recent_tasks(group_id: int, limit: int, tasks: list, ttl_seconds: int = 300):
    try:
        key = f"cache:recent_tasks:{group_id}:{limit}"
        serializable_tasks = []
        for task in tasks:
            task_copy = dict(task)
            for key_name, value in task_copy.items():
                if hasattr(value, 'isoformat'):
                    task_copy[key_name] = value.isoformat()
            serializable_tasks.append(task_copy)
        await redis_client.setex(key, ttl_seconds, json.dumps(serializable_tasks))
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed caching recent_tasks:{group_id}:{limit}: {e}")

async def invalidate_recent_tasks_cache(group_id: int):
    try:
        pattern = f"cache:recent_tasks:{group_id}:*"
        # Async scan over pattern
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"[CACHE INVALIDATE] recent_tasks:{group_id}:* ({len(keys)} keys)")
    except Exception as e:
        logger.error(f"[CACHE ERROR] Failed to invalidate recent_tasks:{group_id}: {e}")
        
# Alias for compatibility with API gateway
invalidate_recent_tasks_cache_async = invalidate_recent_tasks_cache


# ============================================================================
# EDIT STATE MANAGEMENT
# ============================================================================

async def set_edit_task_state(user_id: int, task_data: dict, ttl_seconds: int = 300):
    try:
        key = f"edit_task:{user_id}"
        await redis_client.setex(key, ttl_seconds, json.dumps(task_data))
    except Exception as e:
        logger.error(f"[REDIS ERROR] Failed to set edit state for user {user_id}: {e}")

async def get_edit_task_state(user_id: int) -> Optional[dict]:
    try:
        key = f"edit_task:{user_id}"
        data = await redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"[REDIS ERROR] Failed to get edit state for user {user_id}: {e}")
        return None

async def clear_edit_task_state(user_id: int):
    try:
        key = f"edit_task:{user_id}"
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"[REDIS ERROR] Failed to clear edit state for user {user_id}: {e}")


# ============================================================================
# ROLLING MESSAGE BUFFER
# ============================================================================

async def push_raw_message(group_id: int, message_data: dict, window_size: int = 20, ttl_seconds: int = 7200):
    """
    Push raw message to rolling window BEFORE triage.
    Keeps last window_size messages per group.
    """
    try:
        key = f"raw_msgs:{group_id}"
        # Add to left (newest first)
        await redis_client.lpush(key, json.dumps(message_data))
        # Trim to keep only last N messages
        await redis_client.ltrim(key, 0, window_size - 1)
        # Set expiry
        await redis_client.expire(key, ttl_seconds)
    except Exception as e:
        logger.error(f"[BUFFER ERROR] Failed to push message to buffer:{group_id}: {e}")

async def get_raw_message_window(group_id: int, limit: int = 20) -> list:
    """
    Get the most recent messages from the rolling buffer.
    lpush means index 0 is newest — read 0 to limit-1 for most recent.
    """
    try:
        key = f"raw_msgs:{group_id}"
        raw = await redis_client.lrange(key, 0, limit - 1)
        messages = []
        for item in raw:
            try:
                if isinstance(item, bytes):
                    item = item.decode('utf-8')
                messages.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                continue
        return messages
    except Exception as e:
        logger.error(f"[BUFFER ERROR] Failed to get buffer:{group_id}: {e}")
        return []
