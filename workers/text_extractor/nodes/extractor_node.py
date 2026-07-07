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
    message_buffer = state.get("message_buffer", [])
    
    logger.info("Extractor Node started", extra={
        "node": "extractor_node",
        "intent": intent,
        "message_length": len(message_text),
        "has_context": bool(db_context)
    })
    
    # Get current date and time in IST
    current_datetime_str = get_current_ist_time()
    current_year = get_current_year()
    
    # Choose extraction prompt based on intent
    if intent == "UPDATE":
        result = await extract_update(state, current_datetime_str, current_year)
    elif intent == "ANNOUNCEMENT":
        result = await extract_announcement(state, current_datetime_str, current_year)
    elif intent == "RESOURCE_CALLOUT":
        result = await extract_resource_callout(state, current_datetime_str, current_year)
    else:  # NEW, QUERY, etc.
        result = await extract_new_task(state, current_datetime_str, current_year)
    
    state["extracted_data"] = result
    
    logger.info("Extractor Node completed", extra={
        "node": "extractor_node",
        "extracted_title": result.title if hasattr(result, 'title') else None,
        "message_type": result.message_type if hasattr(result, 'message_type') else None,
        "extracted_deadline": str(result.deadline) if hasattr(result, 'deadline') and result.deadline else None
    })
    
    return state


async def extract_new_task(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    """Extract NEW task with full field support."""
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    message_buffer = state.get("message_buffer", [])
    
    # Include recent chat context for pronoun resolution
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
- ALL dates must be in {current_year} or later

TIME INTERPRETATION:
- "EOD" / "end of day" = 23:59:59
- "COB" / "close of business" = 17:00:00
- "by today" = 23:59:59 today
- "midnight" = 23:59:59 (NOT 00:00:00)
- If no time specified = 23:59:59 on that date

MESSAGE TYPE DETECTION:
- If message mentions a Google Form or form URL → message_type = "form_deadline"
- If message is just informational with no deadline → message_type = "announcement"
- If message is a Q&A exchange → message_type = "qa_pair"
- Otherwise → message_type = "deadline"

APPLIES_AT vs DEADLINE:
- applies_at = when the event HAPPENS (class time, meeting time, lab time)
- deadline = when something is DUE (submission, form filling)
- Example: "Lab test tomorrow at 2pm" → applies_at = 2pm, deadline = 2pm
- Example: "Submit report by Friday 5pm" → deadline = 5pm Friday, applies_at = null

LOCATION EXTRACTION:
- Extract any venue, room, lab, block mentioned
- Examples: "ESB 509", "CSE Lab 1", "Room 304", "Block A", "Apex 709"

REMINDER STRATEGY:
- "standard" = 24h, 1h, deadline reminders (default)
- "morning_of" = single reminder at 8am on the day of the event
- "immediate" = DM right away, no scheduled reminders
- Use "morning_of" for classes, labs, meetings
- Use "immediate" for urgent announcements
- Use "standard" for deadlines, submissions

OUTPUT FORMAT (IST, no timezone suffix):
- deadline: "2026-05-10T23:59:59"
- applies_at: "2026-05-11T14:00:00"

Respond with ONLY a JSON object:
{{
  "event_category": "deadline",
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
  "question_text": null,
  "answer_text": null,
  "match_confidence": null
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def extract_update(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    """Extract UPDATE with match confidence scoring."""
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    update_candidates = state.get("update_candidates", [])
    
    candidates_text = ""
    if update_candidates:
        candidates_text = "Potential matching tasks found:\n"
        for i, task in enumerate(update_candidates, 1):
            candidates_text += f"{i}. {task.get('title')} (deadline: {task.get('deadline')}, match: {task.get('similarity', 0):.2f})\n"
    
    prompt = f"""CRITICAL: Today's date and time is {current_datetime_str}. The current year is {current_year}.

This is an UPDATE message. Extract the NEW deadline/details.

{candidates_text}

Current message: "{message_text}"

TASK:
1. Extract the NEW deadline from the update message
2. Score confidence (0.0-1.0) that we identified the right task to update
3. If multiple candidates exist, pick the best match based on similarity

TIME INTERPRETATION (same as NEW):
- "EOD" = 23:59:59, "COB" = 17:00:00
- If no time specified = 23:59:59
- Output in IST format: "2026-05-10T23:59:59"

Respond with ONLY a JSON object:
{{
  "event_category": "deadline",
  "title": "Submit OS assignment",
  "action_required": "Submit the OS assignment with new deadline",
  "deadline": "2026-05-12T23:59:59",
  "confidence_score": 0.9,
  "needs_clarification": false,
  "message_type": "deadline",
  "applies_at": null,
  "location": null,
  "form_url": null,
  "reminder_strategy": "standard",
  "question_text": null,
  "answer_text": null,
  "match_confidence": 0.85
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def extract_announcement(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    """Extract ANNOUNCEMENT - no deadline, just info."""
    message_text = state.get("message_text", "")
    
    prompt = f"""Extract announcement details from this group message.

Current message: "{message_text}"

This is a GROUP ANNOUNCEMENT with no specific deadline or action required.
Create a descriptive title and set message_type to "announcement".
Set reminder_strategy to "immediate" (send DM right away).

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
  "location": null,
  "form_url": null,
  "reminder_strategy": "immediate",
  "question_text": null,
  "answer_text": null,
  "match_confidence": null
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def extract_resource_callout(state: AgentState, current_datetime_str: str, current_year: int) -> EventExtraction:
    """Extract RESOURCE_CALLOUT - bring/submit/fill something."""
    message_text = state.get("message_text", "")
    db_context = state.get("db_context", "")
    
    prompt = f"""CRITICAL: Today's date and time is {current_datetime_str}. The current year is {current_year}.

Extract resource callout details (bring/submit/fill/collect something).

Database context: {db_context}

Current message: "{message_text}"

RULES:
- If it's a Google Form → message_type = "form_deadline", extract form_url
- If it's bringing something physical → message_type = "deadline"
- Extract deadline if mentioned, otherwise needs_clarification = true
- Extract location if mentioned (where to bring/submit)

TIME INTERPRETATION:
- "EOD" = 23:59:59, "by today" = 23:59:59 today
- If no time specified = 23:59:59 on that date
- Output in IST: "2026-05-10T23:59:59"

Respond with ONLY a JSON object:
{{
  "event_category": "task",
  "title": "Bring lab record",
  "action_required": "Bring OOPS lab record to class",
  "deadline": "2026-05-10T23:59:59",
  "confidence_score": 0.85,
  "needs_clarification": false,
  "message_type": "deadline",
  "applies_at": null,
  "location": "CSE Lab 1",
  "form_url": null,
  "reminder_strategy": "standard",
  "question_text": null,
  "answer_text": null,
  "match_confidence": null
}}"""
    
    return await _call_llm_and_parse(prompt, message_text)


async def _call_llm_and_parse(prompt: str, message_text: str) -> EventExtraction:
    """Call LLM and parse response into EventExtraction."""
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Remove markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result_dict = json.loads(content)
        result = EventExtraction(**result_dict)
        
        # CRITICAL: Convert IST deadline to UTC
        if result.deadline:
            deadline_utc = convert_ist_to_utc(str(result.deadline))
            if deadline_utc:
                result.deadline = deadline_utc
                logger.info(f"Converted deadline to UTC: {deadline_utc}", extra={"node": "extractor_node"})
        
        # Convert applies_at to UTC if present
        if result.applies_at:
            applies_at_utc = convert_ist_to_utc(str(result.applies_at))
            if applies_at_utc:
                result.applies_at = applies_at_utc
                logger.info(f"Converted applies_at to UTC: {applies_at_utc}", extra={"node": "extractor_node"})
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to parse extraction: {e}", extra={"node": "extractor_node"})
        # Fallback
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
