from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.timezone_utils import get_current_ist_time, get_current_year, convert_ist_to_utc
from shared.schemas import EventExtraction
import json


async def extract_event_data(state: AgentState) -> AgentState:
    """
    Intent-specific extraction with different prompts based on intent.
    """
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    intent = state.get("intent", "NEW")
    
    logger.info("Extractor Node started", extra={
        "node": "extractor_node",
        "intent": intent,
        "message_length": len(message_text),
        "has_context": bool(db_context)
    })
    
    current_datetime_str = get_current_ist_time()
    current_year = get_current_year()
    
    if intent == "UPDATE":
        result = await extract_update(state, current_datetime_str, current_year)
    elif intent == "ANNOUNCEMENT":
        result = await extract_announcement(state, current_datetime_str, current_year)
    elif intent == "FORM_DEADLINE":
        result = await extract_form_deadline(state, current_datetime_str, current_year)
    else:  # NEW and anything else
        result = await extract_new_task(state, current_datetime_str, current_year)
    
    state["extracted_data"] = result
    
    logger.info("Extractor Node completed", extra={"node": "extractor_node"})
    
    return state


async def extract_new_task(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    message_buffer = state.get("message_buffer", [])
    
    buffer_context = ""
    if message_buffer and len(message_buffer) > 0:
        buffer_context = "Recent chat messages:\n" + "\n".join([f"- {msg}" for msg in message_buffer[-5:]])
    
    prompt = f"""CRITICAL: Today's date and time is {current_datetime_str}. The current year is {current_year}.

Extract task details from the following message.

{buffer_context}

Database context: {db_context}

Current message: "{message_text}"

IMPORTANT RULES:
- User is in INDIA (IST timezone)
- If user says "tomorrow", calculate from today ({current_datetime_str})
- If user says "10 May" without year, assume {current_year}
- If user says "10 PM", they mean 10 PM IST

TIME INTERPRETATION:
- "EOD" / "end of day" = 23:59:59
- "COB" / "close of business" = 17:00:00
- "by today" = 23:59:59 today
- "midnight" = 23:59:59
- If no time specified = 23:59:59 on that date

Respond with ONLY a JSON object:
{{
  "event_category": "task",
  "title": "Submit OS assignment",
  "action_required": "Submit the OS assignment",
  "deadline": "2026-05-10T23:59:59",
  "confidence_score": 0.9,
  "needs_clarification": false,
  "message_type": "deadline",
  "applies_at": null,
  "location": null,
  "form_url": null,
  "reminder_strategy": "standard",
  "match_confidence": null
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def extract_update(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    message_text = state.get("message_text", "")
    update_candidates = state.get("update_candidates", [])
    
    candidates_text = ""
    if update_candidates:
        candidates_text = "Potential matching tasks found:\n"
        for i, task in enumerate(update_candidates, 1):
            candidates_text += f"{i}. {task.get('title')} (deadline: {task.get('deadline')})\n"
    
    prompt = f"""CRITICAL: Today's date and time is {current_datetime_str}. The current year is {current_year}.

This is an UPDATE message. Extract the NEW deadline.

{candidates_text}

Current message: "{message_text}"

Respond with ONLY a JSON object:
{{
  "event_category": "task",
  "title": "Update task",
  "action_required": "Update deadline",
  "deadline": "2026-05-12T23:59:59",
  "confidence_score": 0.9,
  "needs_clarification": false,
  "message_type": "deadline",
  "applies_at": null,
  "location": null,
  "form_url": null,
  "reminder_strategy": "standard",
  "match_confidence": 0.85
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def extract_announcement(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    message_text = state.get("message_text", "")
    
    prompt = f"""Extract announcement details from this group message.

Current message: "{message_text}"

This is a GROUP ANNOUNCEMENT with no specific deadline or action required.
Create a descriptive title and set message_type to "announcement".
Set reminder_strategy to "immediate" or "morning_of".

Respond with ONLY a JSON object:
{{
  "event_category": "announcement",
  "title": "Internship results announced",
  "action_required": "Check internship results on portal",
  "deadline": null,
  "confidence_score": 0.95,
  "needs_clarification": false,
  "message_type": "announcement",
  "applies_at": null,
  "location": "Portal",
  "form_url": null,
  "reminder_strategy": "immediate",
  "match_confidence": null
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def extract_form_deadline(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    message_text = state.get("message_text", "")
    
    prompt = f"""Extract form deadline details from this group message.

Current message: "{message_text}"

This is a FORM DEADLINE message containing a URL.
Create a descriptive title, set message_type to "form_deadline".
Extract the form URL and the deadline.

Respond with ONLY a JSON object:
{{
  "event_category": "task",
  "title": "Fill Feedback Form",
  "action_required": "Fill the feedback form",
  "deadline": "2026-05-10T23:59:59",
  "confidence_score": 0.95,
  "needs_clarification": false,
  "message_type": "form_deadline",
  "applies_at": null,
  "location": null,
  "form_url": "https://forms.gle/abc123xyz",
  "reminder_strategy": "standard",
  "match_confidence": null
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def _call_llm_and_parse(prompt: str, message_text: str) -> EventExtraction:
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result_dict = json.loads(content)
        result = EventExtraction(**result_dict)
        
        if result.deadline:
            deadline_utc = convert_ist_to_utc(str(result.deadline))
            if deadline_utc:
                result.deadline = deadline_utc
        
        if result.applies_at:
            applies_at_utc = convert_ist_to_utc(str(result.applies_at))
            if applies_at_utc:
                result.applies_at = applies_at_utc
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to parse extraction: {e}")
        return EventExtraction(
            event_category="task",
            title=message_text[:50],
            action_required=message_text,
            deadline=None,
            confidence_score=0.5,
            needs_clarification=True,
            message_type="deadline",
            reminder_strategy="standard"
        )
