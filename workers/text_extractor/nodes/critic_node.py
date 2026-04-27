from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.metrics import hitl_triggers

def critique_extraction(state: AgentState) -> AgentState:
    extracted_data = state.get("extracted_data")
    
    logger.info("Critic Node started", extra={
        "node": "critic_node",
        "has_extracted_data": bool(extracted_data)
    })
    
    state["needs_human"] = False
    state["validation_error"] = None
    
    if extracted_data:
        if extracted_data.event_category in ["meeting", "deadline", "task"] and not extracted_data.deadline:
            state["needs_human"] = True
            state["validation_error"] = "Missing deadline for event."
            hitl_triggers.labels(error_type="missing_deadline").inc()
            logger.warning("Critic Node validation error", extra={
                "node": "critic_node",
                "validation_error": "Missing deadline for event",
                "event_category": extracted_data.event_category
            })
        
        if extracted_data.needs_clarification:
            state["needs_human"] = True
            state["validation_error"] = "LLM indicated clarification is needed."
            hitl_triggers.labels(error_type="llm_clarification_needed").inc()
            logger.warning("Critic Node validation error", extra={
                "node": "critic_node",
                "validation_error": "LLM indicated clarification is needed"
            })
    
    logger.info("Critic Node completed", extra={
        "node": "critic_node",
        "needs_human": state["needs_human"],
        "validation_error": state["validation_error"]
    })
            
    return state
