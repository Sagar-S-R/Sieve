from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import set_hitl_lock
from workers.text_extractor.services.telegram_client import send_dm
from workers.text_extractor.core.logger import logger
import asyncio


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
        
        # Send Telegram DM to user
        try:
            asyncio.run(send_dm(user_id, state["hitl_prompt"]))
            logger.info("HITL DM sent successfully", extra={
                "node": "hitl_node",
                "user_id": user_id
            })
        except Exception as e:
            logger.error(f"Failed to send HITL DM: {e}", extra={
                "node": "hitl_node",
                "user_id": user_id,
                "error": str(e)
            })
    
    return state
