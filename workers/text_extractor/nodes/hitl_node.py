from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import set_hitl_lock
from workers.text_extractor.services.telegram_client import send_dm
from workers.text_extractor.core.logger import logger
import asyncio


def require_human_in_loop(state: AgentState) -> AgentState:
    """Trigger HITL when clarification needed - sends DM to all group subscribers."""
    if state.get("needs_human"):
        group_id = state.get("group_id")
        message_sender_id = state.get("user_id")
        extracted_data = state.get("extracted_data")
        validation_error = state.get("validation_error", "needs clarification")
        
        logger.info("HITL Node triggered", extra={
            "node": "hitl_node",
            "group_id": group_id,
            "message_sender_id": message_sender_id,
            "validation_error": validation_error
        })
        
        title = extracted_data.title if extracted_data else 'unknown task'
        state["hitl_prompt"] = f"I found a task '{title}' but I'm missing some info: {validation_error}. Can you provide it?"
        
        logger.info("HITL clarification prompt created", extra={
            "node": "hitl_node",
            "prompt": state["hitl_prompt"]
        })
        
        # Get all subscribers for this group
        from workers.text_extractor.services.database import get_group_subscribers
        subscribers = asyncio.run(get_group_subscribers(group_id))
        
        if not subscribers:
            logger.warning(f"No subscribers found for group {group_id}", extra={"node": "hitl_node"})
            return state
        
        logger.info(f"Found {len(subscribers)} subscriber(s) for group {group_id}", extra={"node": "hitl_node"})
        
        # Save state to Redis for each subscriber and send DM
        for subscriber_id in subscribers:
            # Save state to Redis with subscriber's ID
            set_hitl_lock(subscriber_id, state)
            
            logger.info(f"HITL Redis lock created for subscriber {subscriber_id}", extra={
                "node": "hitl_node",
                "subscriber_id": subscriber_id
            })
            
            # Send Telegram DM to subscriber
            try:
                asyncio.run(send_dm(subscriber_id, state["hitl_prompt"]))
                logger.info(f"HITL DM sent successfully to subscriber {subscriber_id}", extra={
                    "node": "hitl_node",
                    "subscriber_id": subscriber_id
                })
            except Exception as e:
                logger.error(f"Failed to send HITL DM to subscriber {subscriber_id}: {e}", extra={
                    "node": "hitl_node",
                    "subscriber_id": subscriber_id,
                    "error": str(e)
                })
    
    return state
