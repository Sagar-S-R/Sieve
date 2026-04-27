from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from shared.schemas import EventExtraction

def extract_event_data(state: AgentState) -> AgentState:
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    
    logger.info("Extractor Node started", extra={
        "node": "extractor_node",
        "message_length": len(message_text),
        "has_context": bool(db_context)
    })
    
    prompt = f"""
    Extract event details from the following message.
    Context from past messages: {db_context}
    
    Message: {message_text}
    """
    
    structured_llm = llm.with_structured_output(EventExtraction)
    result = structured_llm.invoke(prompt)
    
    state["extracted_data"] = result
    
    logger.info("Extractor Node completed", extra={
        "node": "extractor_node",
        "extracted_title": result.title if hasattr(result, 'title') else None,
        "extracted_action": result.action_required if hasattr(result, 'action_required') else None,
        "extracted_deadline": str(result.deadline) if hasattr(result, 'deadline') else None
    })
    
    return state
