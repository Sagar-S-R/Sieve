from workers.media_extractor.graph.state import AgentState
from shared.redis_client import set_hitl_lock


async def require_human_in_loop(state: AgentState) -> AgentState:
    """
    Trigger HITL flow when clarification is needed.
    Creates Redis lock and formats prompt for user.
    """
    if state.get("needs_human"):
        user_id = state.get("user_id")
        extracted_data = state.get("extracted_data")
        validation_error = state.get("validation_error", "needs clarification")
        
        title = extracted_data.title if extracted_data else 'unknown task'
        state["hitl_prompt"] = (
            f"I found a task '{title}' in your media but I'm missing some info: "
            f"{validation_error}. Can you provide it?"
        )
        
        # Save current state to Redis lock
        await set_hitl_lock(user_id, state)
        
        print(f"[HITL] Triggered for user {user_id}. Prompt: {state['hitl_prompt']}")
    
    return state
