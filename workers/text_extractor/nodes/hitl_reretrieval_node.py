"""
HITL Reretrieval Node — Scenario 3 (UPDATE Confirmation)

Called by critic_node when intent=UPDATE and update_candidates exist but no task
has been confirmed yet. This node:
  1. Picks the best candidate (highest similarity) or lists all candidates.
  2. Sends a confirmation DM to the user: "Updating X to Y — confirm? Yes/No"
  3. Saves the proposed update in the HITL Redis lock.
  4. Returns with needs_human=True so the graph ends here.

Resolution happens in main.py when the user replies:
  - "yes"  → direct DB update (no LLM)
  - "no"   → ask which task, re-run pipeline
  - number → pick from list, move to update_confirmation
"""

from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.telegram_client import send_telegram_message
from workers.text_extractor.core.logger import logger


_HIGH_CONFIDENCE_THRESHOLD = 0.80


async def hitl_update_confirmation(state: AgentState) -> AgentState:
    """
    Present the matched task(s) to the user for confirmation before any DB write.

    High confidence (≥ 0.80): show single confirmation — "Updating X to Y — yes/no?"
    Low confidence  (< 0.80): show numbered list — "Which task? Reply 1, 2, or 3."
    """
    user_id   = state.get("user_id")
    group_id  = state.get("group_id")
    is_personal = state.get("is_personal", False)
    candidates  = state.get("update_candidates", [])
    extracted   = state.get("extracted_data")

    if not candidates:
        # No candidates found — fall through to end without touching DB
        logger.warning("hitl_reretrieval_node: no candidates, ending silently", extra={"node": "hitl_reretrieval"})
        state["needs_human"] = False
        return state

    new_deadline_str = str(extracted.deadline) if extracted and extracted.deadline else "new deadline"

    best = candidates[0]  # context_node returns candidates sorted by similarity desc
    best_score = best.get("similarity", 0.0)

    if best_score >= _HIGH_CONFIDENCE_THRESHOLD:
        # --- High confidence: single-task confirmation ---
        msg = (
            f"Updating *\"{best['title']}\"* → deadline: *{new_deadline_str}*\n\n"
            f"Is this correct? Reply *yes* or *no*."
        )
        hitl_reason = "update_confirmation"
        proposed_task_id = best["id"]

    else:
        # --- Low confidence: numbered list ---
        lines = [" *Multiple tasks found — which one are you updating?*\n"]
        for i, task in enumerate(candidates, 1):
            title    = task.get("title", "Untitled")
            deadline = task.get("deadline", "no deadline")
            score    = task.get("similarity", 0.0)
            lines.append(f"{i}. {title}\n   Deadline: {deadline}  (match {score:.0%})")
        lines.append(f"\nNew deadline you mentioned: *{new_deadline_str}*")
        lines.append("\n*Reply with the number* (e.g. '1') or describe the task again.")

        msg = "\n".join(lines)
        hitl_reason = "low_match_confidence"
        proposed_task_id = None

    # Send DM to user (personal flow) or to group (group flow)
    target = user_id if is_personal else group_id
    sent = await send_telegram_message(target, msg)
    bot_message_id = sent.get("result", {}).get("message_id") if sent else None

    # Save HITL lock so main.py can resolve on next reply
    hitl_state = {
        "group_id":            group_id,
        "is_personal":         is_personal,
        "original_message":    state.get("original_message") or state.get("message_text"),
        "intent":              "UPDATE",
        "extracted_data":      extracted.model_dump() if extracted else None,
        "update_candidates":   candidates,
        "excluded_task_ids":   state.get("excluded_task_ids", []),
        "proposed_task_id":    proposed_task_id,
        "proposed_new_value":  new_deadline_str,
        "hitl_reason":         hitl_reason,
        "hitl_round":          state.get("hitl_round", 0) + 1,
        "bot_message_id":      bot_message_id,
    }

    from shared.redis_client import set_hitl_lock, set_group_hitl_lock
    if not is_personal and group_id:
        await set_group_hitl_lock(group_id, hitl_state)
    else:
        await set_hitl_lock(user_id, hitl_state)

    state["needs_human"] = True
    state["hitl_reason"] = hitl_reason
    state["hitl_prompt"] = msg

    logger.info(
        f"hitl_reretrieval_node: sent confirmation to {'user' if is_personal else 'group'}, "
        f"reason={hitl_reason}, candidates={len(candidates)}",
        extra={"node": "hitl_reretrieval"}
    )
    return state
