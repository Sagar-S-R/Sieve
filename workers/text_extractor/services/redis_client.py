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
