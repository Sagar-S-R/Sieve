from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.redis_client import set_group_hitl_lock
from workers.text_extractor.services.telegram_client import send_telegram_message
from workers.text_extractor.core.logger import logger


async def require_human_in_loop(state: AgentState) -> AgentState:
    """Send ONE clarification message to the GROUP chat. First valid reply wins."""
    if not state.get("needs_human"):
        return state

    group_id = state.get("group_id")
    extracted = state.get("extracted_data")
    hitl_reason = state.get("hitl_reason")
    candidate_tasks = state.get("update_candidates", [])

    message = _build_group_hitl_message(hitl_reason, extracted, candidate_tasks)

    # Send to GROUP and capture the bot's message_id for reply matching
    sent = await send_telegram_message(group_id, message)
    bot_message_id = sent.get("result", {}).get("message_id") if sent else None

    hitl_state = {
        "group_id": group_id,
        "original_message": state.get("original_message") or state.get("message_text"),
        "intent": state.get("intent"),
        "extracted_data": extracted.model_dump() if extracted else None,
        "update_candidates": candidate_tasks,
        "excluded_task_ids": state.get("excluded_task_ids", []),
        "proposed_task_id": state.get("selected_task_id"),
        "proposed_new_value": (
            str(extracted.deadline) if extracted and extracted.deadline
            else (extracted.location if extracted else None)
        ),
        "hitl_reason": hitl_reason or state.get("validation_error"),
        "hitl_round": state.get("hitl_round", 0) + 1,
        "bot_message_id": bot_message_id,
        "validation_error": state.get("validation_error"),
    }

    set_group_hitl_lock(group_id, hitl_state)

    logger.info(f"[HITL] Group clarification sent to {group_id}, bot_message_id={bot_message_id}")
    return state


def _build_group_hitl_message(reason: str, extracted, candidate_tasks: list) -> str:
    title = extracted.title if extracted else "unknown task"

    if reason == "missing_deadline":
        return (
            f"Task detected: *{title}*\n\n"
            f"What's the deadline?\n\n"
            f"*Reply to THIS message* with the date and time\n"
            f"_(First reply will be used)_"
        )

    elif reason == "missing_location":
        return (
            f"Venue change detected\n\n"
            f"Which room or building?\n\n"
            f"*Reply to THIS message* with the location\n"
            f"_(First reply will be used)_"
        )

    elif reason == "missing_url":
        return (
            f"Form deadline detected: *{title}*\n\n"
            f"Can you share the form link?\n\n"
            f"*Reply to THIS message* with the URL\n"
            f"_(First reply will be used)_"
        )

    elif reason in ["low_match_confidence", "update_confirmation"]:
        task_list = "\n".join([
            f"{i+1}. {t['title']} -- {t.get('deadline', 'no deadline')}"
            for i, t in enumerate(candidate_tasks)
        ])
        return (
            f"Which task are you updating?\n\n"
            f"{task_list}\n\n"
            f"*Reply to THIS message* with the number\n"
            f"_(First reply will be used)_"
        )

    else:
        clarification = extracted.needs_clarification if extracted else "Please clarify"
        return (
            f"Task detected: *{title}*\n\n"
            f"{clarification}\n\n"
            f"*Reply to THIS message* with your answer\n"
            f"_(First reply will be used)_"
        )
