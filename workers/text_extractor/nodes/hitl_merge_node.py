from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
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
    original_message = state.get("db_context", "")  # We'll store original message here
    clarification = state.get("message_text", "")
    extracted_data = state.get("extracted_data", {})
    
    # Build prompt to merge clarification
    prompt = f"""You are helping complete a task extraction. The user provided clarification.

Original extraction:
- Title: {extracted_data.get('title', 'Unknown')}
- Action: {extracted_data.get('action_required', 'Unknown')}
- Deadline: {extracted_data.get('deadline', 'Missing')}

User's clarification: "{clarification}"

Parse the clarification and provide the COMPLETE task details with the clarification merged in.
If the clarification is a deadline, parse it into ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).
If the clarification adds context to the title or action, merge it appropriately.

Respond with ONLY a JSON object:
{{
  "event_category": "deadline",
  "title": "Complete title",
  "action_required": "Complete action description",
  "deadline": "2026-05-10T23:59:59Z",
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
