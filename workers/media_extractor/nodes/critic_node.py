from workers.media_extractor.graph.state import AgentState


def critique_extraction(state: AgentState) -> AgentState:
    """
    Validate extracted data. Check if deadline is missing for important events.
    """
    extracted_data = state.get("extracted_data")
    
    state["needs_human"] = False
    state["validation_error"] = None
    
    if extracted_data:
        # Check if deadline is missing for events that need one
        if extracted_data.event_category in ["meeting", "deadline", "task"] and not extracted_data.deadline:
            state["needs_human"] = True
            state["validation_error"] = "Missing deadline for event."
        
        # Check if LLM indicated clarification is needed
        if extracted_data.needs_clarification:
            state["needs_human"] = True
            state["validation_error"] = "LLM indicated clarification is needed."
    
    return state
