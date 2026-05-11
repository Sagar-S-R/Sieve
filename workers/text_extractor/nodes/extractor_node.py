from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.timezone_utils import get_current_ist_time, get_current_year, convert_ist_to_utc
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
    
    # Get current date and time in IST
    current_datetime_str = get_current_ist_time()
    current_year = get_current_year()
    
    prompt = f"""CRITICAL: Today's date and time is {current_datetime_str}. The current year is {current_year}.

Extract event details from the following message.
Context from past messages: {db_context}

Message: {message_text}

IMPORTANT RULES:
- User is in INDIA (IST timezone)
- If user says "tomorrow", calculate from today ({current_datetime_str})
- If user says "10 May" without year, assume {current_year}
- If user says "10 PM", they mean 10 PM IST
- ALL dates must be in {current_year} or later (never 2024 or earlier)

OUTPUT FORMAT:
- Output deadline in IST time (NOT UTC)
- Format: YYYY-MM-DDTHH:MM:SS (no Z suffix, no timezone)
- Example: "2026-05-10T22:00:00" for 10 PM IST on May 10, 2026

CLARIFICATION RULES:
- If message is vague (just "deadline" or "form" without details), set needs_clarification=true
- If no specific time mentioned, set needs_clarification=true
- If title would be generic (like "Fee payment"), set needs_clarification=true

Respond with ONLY a JSON object in this format:
{{
  "event_category": "deadline",
  "title": "Submit assignment",
  "action_required": "Submit the assignment",
  "deadline": "2026-05-10T17:00:00Z",
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
        
        # CRITICAL: Convert IST deadline to UTC in code (don't trust LLM)
        if result.deadline:
            deadline_utc = convert_ist_to_utc(str(result.deadline))
            if deadline_utc:
                result.deadline = deadline_utc
                logger.info(f"Converted deadline to UTC: {deadline_utc}", extra={"node": "extractor_node"})
            else:
                logger.warning("Failed to convert deadline to UTC", extra={"node": "extractor_node"})
        
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
