from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.metrics import hitl_triggers

async def critique_extraction(state: AgentState) -> AgentState:
    extracted_data = state.get("extracted_data")
    
    logger.info("Critic Node started", extra={
        "node": "critic_node",
        "has_extracted_data": bool(extracted_data)
    })
    
    state["needs_human"] = False
    state["validation_error"] = None
    
    if extracted_data:
        # Check 1: Missing deadline for time-sensitive events
        if extracted_data.event_category in ["meeting", "deadline", "task"] and not extracted_data.deadline:
            state["needs_human"] = True
            state["validation_error"] = "Missing deadline for event."
            hitl_triggers.labels(error_type="missing_deadline").inc()
            logger.warning("Critic Node validation error", extra={
                "node": "critic_node",
                "validation_error": "Missing deadline for event",
                "event_category": extracted_data.event_category
            })
        
        # Check 2: LLM explicitly requested clarification
        if extracted_data.needs_clarification:
            state["needs_human"] = True
            state["validation_error"] = "LLM indicated clarification is needed."
            hitl_triggers.labels(error_type="llm_clarification_needed").inc()
            logger.warning("Critic Node validation error", extra={
                "node": "critic_node",
                "validation_error": "LLM indicated clarification is needed"
            })
        
        # Check 3: Vague or generic titles (likely incomplete extraction)
        vague_keywords = ["form", "deadline", "payment", "fee", "submit", "registration"]
        title_lower = extracted_data.title.lower()
        action_lower = extracted_data.action_required.lower()
        
        # If title is too short or contains only vague keywords without specifics
        if len(extracted_data.title.split()) <= 3:
            has_vague = any(keyword in title_lower for keyword in vague_keywords)
            has_specific = any(char.isdigit() for char in extracted_data.title) or len(extracted_data.title.split()) > 4
            
            if has_vague and not has_specific:
                state["needs_human"] = True
                state["validation_error"] = f"Title '{extracted_data.title}' is too vague. What specifically needs to be done?"
                hitl_triggers.labels(error_type="vague_title").inc()
                logger.warning("Critic Node validation error", extra={
                    "node": "critic_node",
                    "validation_error": "Vague title detected",
                    "title": extracted_data.title
                })
        
        # Check 4: Action is just a repeat of title (no real information)
        if extracted_data.title.lower() == extracted_data.action_required.lower():
            state["needs_human"] = True
            state["validation_error"] = "Need more details about what needs to be done."
            hitl_triggers.labels(error_type="duplicate_title_action").inc()
            logger.warning("Critic Node validation error", extra={
                "node": "critic_node",
                "validation_error": "Title and action are identical"
            })
        
        # Check 5: Low confidence score
        if hasattr(extracted_data, 'confidence_score') and extracted_data.confidence_score < 0.7:
            state["needs_human"] = True
            state["validation_error"] = "Need more details to extract the task accurately."
            hitl_triggers.labels(error_type="low_confidence").inc()
            logger.warning("Critic Node validation error", extra={
                "node": "critic_node",
                "validation_error": "Low confidence score",
                "confidence": extracted_data.confidence_score
            })
    
    logger.info("Critic Node completed", extra={
        "node": "critic_node",
        "needs_human": state["needs_human"],
        "validation_error": state["validation_error"]
    })
            
    return state
