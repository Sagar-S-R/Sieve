from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.logger import logger
from shared.metrics import validation_failures


async def critique_extraction(state: AgentState) -> AgentState:
    intent = state.get("intent")
    extracted = state.get("extracted_data")

    logger.info("Critic Node started", extra={
        "node": "critic_node",
        "intent": intent,
        "has_extraction": bool(extracted)
    })

    if not extracted:
        state["needs_human"] = True
        state["validation_error"] = "extraction_failed"
        return state

    if intent == "UPDATE":
        candidate_tasks = state.get("update_candidates", [])
        if candidate_tasks:
            # Found candidates — ask user to pick
            state["needs_human"] = True
            state["hitl_reason"] = "update_candidates"
            state["validation_error"] = None
        else:
            # No candidates found — treat as NEW
            state["intent"] = "NEW"
            state["needs_human"] = False

    elif intent == "NEW":
        if not extracted.deadline:
            state["needs_human"] = True
            state["hitl_reason"] = "missing_deadline"
        elif extracted.needs_clarification:
            state["needs_human"] = True
            state["hitl_reason"] = "llm_requested"

    elif intent == "ANNOUNCEMENT":
        # Usually ANNOUNCEMENT does not strictly require location or deadline, but if it's missing location we don't block
        state["needs_human"] = False

    elif intent == "FORM_DEADLINE":
        if not extracted.form_url:
            state["needs_human"] = True
            state["hitl_reason"] = "missing_url"
        elif not extracted.deadline:
            state["needs_human"] = True
            state["hitl_reason"] = "missing_deadline"

    if state.get("needs_human"):
        validation_failures.labels(reason=state.get("hitl_reason", "unknown")).inc()
        logger.info(f"Critic flagged for HITL: {state.get('hitl_reason')}", extra={"node": "critic_node"})
    else:
        logger.info("Critic passed extraction", extra={"node": "critic_node"})

    return state
