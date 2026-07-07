"""
HITL Reretrieval Node - Handles UPDATE confirmation flow.

When intent=UPDATE and we found multiple candidates, we need user confirmation:
1. Send DM listing candidates with numbers
2. User replies with a number
3. We parse the number and confirm selection
4. Route back to extraction with confirmed task ID
"""

from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.telegram_client import send_telegram_message
from workers.text_extractor.core.logger import logger


async def hitl_update_confirmation(state: AgentState) -> AgentState:
    """
    Handle UPDATE confirmation flow.
    
    If update_candidates exist and no selected_task_id yet:
        - Send DM asking user to confirm which task to update
        - Set HITL lock with candidates
        - Return with needs_human=True
    
    If user has replied with a number:
        - Parse selection
        - Set selected_task_id
        - Clear needs_human
        - Workflow will proceed to update the selected task
    """
    user_id = state.get("user_id")
    group_id = state.get("group_id")
    update_candidates = state.get("update_candidates", [])
    selected_task_id = state.get("selected_task_id")
    message_text = state.get("message_text", "")
    
    logger.info("HITL Update Confirmation Node started", extra={
        "node": "hitl_reretrieval",
        "user_id": user_id,
        "candidates_count": len(update_candidates),
        "has_selection": bool(selected_task_id)
    })
    
    # Case 1: User is responding with a selection number
    if selected_task_id is None and update_candidates:
        # Check if message_text is a number (user's selection)
        try:
            selection = int(message_text.strip())
            
            if 1 <= selection <= len(update_candidates):
                # Valid selection
                selected_task = update_candidates[selection - 1]
                state["selected_task_id"] = selected_task["id"]
                state["updating_task_title"] = selected_task["title"]
                state["needs_human"] = False  # Clear HITL flag
                
                logger.info(f"User selected task #{selection}: {selected_task['title']}", extra={
                    "node": "hitl_reretrieval",
                    "selected_task_id": selected_task["id"]
                })
                
                # Send confirmation
                confirmation_msg = f" Updating: \"{selected_task['title']}\"\n\nProcessing your update..."
                await send_telegram_message(user_id, confirmation_msg)
                
                return state
            else:
                # Invalid number
                error_msg = f" Invalid selection. Please choose a number between 1 and {len(update_candidates)}."
                await send_telegram_message(user_id, error_msg)
                state["needs_human"] = True
                return state
                
        except ValueError:
            # Not a number - could be a new message, not a selection
            # Send reminder
            reminder_msg = " Please reply with the task number you want to update (e.g., type '1', '2', etc.)"
            await send_telegram_message(user_id, reminder_msg)
            state["needs_human"] = True
            return state
    
    # Case 2: First time asking for confirmation
    if update_candidates and not selected_task_id:
        # Build candidate list message
        prompt_lines = [
            " <b>Multiple tasks found. Which one do you want to update?</b>\n"
        ]
        
        for i, task in enumerate(update_candidates, 1):
            title = task.get("title", "Untitled")
            deadline = task.get("deadline", "No deadline")
            similarity = task.get("similarity", 0.0)
            
            prompt_lines.append(f"{i}. {title}")
            prompt_lines.append(f"   Deadline: {deadline}")
            prompt_lines.append(f"   Match score: {similarity:.2f}\n")
        
        prompt_lines.append(" <b>Reply with the number</b> (e.g., type '1' to select the first task)")
        
        hitl_prompt = "\n".join(prompt_lines)
        
        # Send to user
        await send_telegram_message(user_id, hitl_prompt)
        
        # Set HITL lock (will be checked on next message)
        from workers.text_extractor.services.redis_client import set_hitl_lock
        set_hitl_lock(user_id, {
            "group_id": group_id,
            "intent": "UPDATE",
            "update_candidates": update_candidates,
            "original_message": state.get("message_text"),
            "extracted_data": state.get("extracted_data").model_dump() if state.get("extracted_data") else None
        })
        
        state["needs_human"] = True
        state["hitl_prompt"] = hitl_prompt
        
        logger.info("HITL update confirmation sent", extra={
            "node": "hitl_reretrieval",
            "user_id": user_id
        })
        
        return state
    
    # Case 3: No candidates or already selected - should not reach here
    logger.warning("HITL reretrieval node reached unexpected state", extra={
        "node": "hitl_reretrieval",
        "has_candidates": bool(update_candidates),
        "has_selection": bool(selected_task_id)
    })
    
    state["needs_human"] = False
    return state
