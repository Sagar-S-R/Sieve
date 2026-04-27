from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import set_hitl_lock
from workers.text_extractor.core.logger import logger


def require_human_in_loop(state: AgentState) -> AgentState:
    """Trigger HITL when clarification needed."""
    if state.get("needs_human"):
        user_id = state.get("user_id")
        extracted_data = state.get("extracted_data")
        validation_error = state.get("validation_error", "needs clarification")
        
        logger.info("HITL Node triggered", extra={
            "node": "hitl_node",
            "user_id": user_id,
            "validation_error": validation_error
        })
        
        title = extracted_data.title if extracted_data else 'unknown task'
        state["hitl_prompt"] = f"I found a task '{title}' but I'm missing some info: {validation_error}. Can you provide it?"
        
        logger.info("HITL clarification prompt created", extra={
            "node": "hitl_node",
            "user_id": user_id,
            "prompt": state["hitl_prompt"]
        })
        
        # Save state to Redis
        set_hitl_lock(user_id, state)
        
        logger.info("HITL Redis lock created", extra={
            "node": "hitl_node",
            "user_id": user_id
        })
        
        # TODO: Send Telegram DM to user with hitl_prompt
        logger.info("HITL DM sending (TODO)", extra={
            "node": "hitl_node",
            "user_id": user_id,
            "action": "send_telegram_dm"
        })
    
    return state
