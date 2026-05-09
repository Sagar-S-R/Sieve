from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from shared.schemas import EventExtraction
import json

def extract_event_data(state: AgentState) -> AgentState:
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    
    logger.info("Extractor Node started", extra={
        "node": "extractor_node",
        "message_length": len(message_text),
        "has_context": bool(db_context)
    })
    
    prompt = f"""Extract event details from the following message.
Context from past messages: {db_context}

Message: {message_text}

Respond with ONLY a JSON object in this format:
{{
  "event_category": "deadline",
  "title": "Submit assignment",
  "action_required": "Submit the assignment",
  "deadline": "2026-05-04T17:00:00Z",
  "confidence_score": 0.9,
  "needs_clarification": false
}}

Categories: meeting, deadline, task, reminder, appointment
Confidence score: 0.0 to 1.0 (how confident you are in the extraction)
needs_clarification: true if deadline or important details are missing/ambiguous"""
    
    response = llm.invoke(prompt)
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response
        content = response.content.strip()
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result_dict = json.loads(content)
        result = EventExtraction(**result_dict)
    except Exception as e:
        logger.error(f"Failed to parse extraction: {e}", extra={"node": "extractor_node", "response": response.content[:200]})
        # Fallback with minimal data
        result = EventExtraction(
            event_category="task",
            title=message_text[:50],
            action_required=message_text,
            deadline=None,
            confidence_score=0.5,
            needs_clarification=True
        )
    
    state["extracted_data"] = result
    
    logger.info("Extractor Node completed", extra={
        "node": "extractor_node",
        "extracted_title": result.title if hasattr(result, 'title') else None,
        "extracted_action": result.action_required if hasattr(result, 'action_required') else None,
        "extracted_deadline": str(result.deadline) if hasattr(result, 'deadline') else None
    })
    
    return state
