from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.timezone_utils import get_current_ist_time, get_current_year, convert_ist_to_utc
from shared.schemas import EventExtraction
import json


def merge_hitl_clarification(state: AgentState) -> AgentState:
    """
    Merge user's clarification with original extracted data.
    Uses LLM to parse the clarification and update the extraction.
    """
    logger.info("HITL Merge Node started", extra={
        "node": "hitl_merge_node",
        "user_id": state.get("user_id")
    })
    
    # Get original extraction and user's clarification
    original_message = state.get("db_context", "")  # Original message
    clarification = state.get("message_text", "")
    extracted_data = state.get("extracted_data", {})
    
    # Get current time in IST
    current_datetime_str = get_current_ist_time()
    current_year = get_current_year()
    
    # Build prompt to merge clarification
    prompt = f"""CRITICAL: Today's date and time is {current_datetime_str}. The current year is {current_year}.

You are helping complete a task extraction. The user provided clarification.

Original message: "{original_message}"

Original extraction:
- Title: {extracted_data.get('title', 'Unknown')}
- Action: {extracted_data.get('action_required', 'Unknown')}
- Deadline: {extracted_data.get('deadline', 'Missing')}

User's clarification: "{clarification}"

IMPORTANT RULES:
- User is in INDIA (IST timezone)
- If clarification mentions time like "6 PM tomorrow", calculate the actual date from today ({current_datetime_str})
- Output deadline in IST format: YYYY-MM-DDTHH:MM:SS (no Z, no timezone suffix)
- Example: "2026-05-12T18:00:00" for 6 PM IST on May 12, 2026
- Merge the clarification with original extraction to create complete task details

TIME INTERPRETATION RULES:
- "EOD" (End of Day) = 23:59:59 (11:59 PM)
- "end of day" = 23:59:59 (11:59 PM)
- "by end of day" = 23:59:59 (11:59 PM)
- "COB" (Close of Business) = 17:00:00 (5 PM)
- "by today" = 23:59:59 today
- "by tonight" = 23:59:59 today
- "midnight" = 23:59:59 (NOT 00:00:00 of next day)
- If no time specified but date given = 23:59:59 on that date

Respond with ONLY a JSON object (no explanations):
{{
  "event_category": "deadline",
  "title": "Complete specific title",
  "action_required": "Complete action description",
  "deadline": "2026-05-12T18:00:00",
  "confidence_score": 0.9,
  "needs_clarification": false
}}"""
    
    try:
        response = llm.invoke(prompt)
        
        # Parse JSON from response
        content = response.content.strip()
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
                logger.info(f"HITL: Converted deadline to UTC: {deadline_utc}", extra={"node": "hitl_merge_node"})
            else:
                logger.warning("HITL: Failed to convert deadline to UTC", extra={"node": "hitl_merge_node"})
        
        state["extracted_data"] = result
        state["needs_human"] = False  # Clarification complete
        
        logger.info("HITL Merge Node completed", extra={
            "node": "hitl_merge_node",
            "merged_title": result.title,
            "merged_deadline": str(result.deadline)
        })
        
    except Exception as e:
        logger.error(f"HITL merge failed: {e}", extra={
            "node": "hitl_merge_node",
            "error": str(e)
        })
        # Keep original extraction
    
    return state
