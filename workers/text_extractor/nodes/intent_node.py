from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.metrics import messages_processed
import json

def classify_intent(state: AgentState) -> AgentState:
    logger.info("Intent Node started", extra={
        "node": "intent_node",
        "message_text": state.get("message_text", "")[:100]  # Log first 100 chars
    })
    
    message_text = state.get("message_text", "")
    
    # Check if API key is set
    from workers.text_extractor.core.config import settings
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set!", extra={"node": "intent_node"})
        # Use fallback immediately
        intent = "NEW"  # Default to NEW if API key missing
        state["intent"] = intent
        return state
    
    logger.info(f"Calling Groq API with message: {message_text[:50]}...", extra={"node": "intent_node"})
    
    prompt = f"""You are an intent classifier for a reminder extraction system. Classify the following message.

INTENT CATEGORIES:

1. NEW - Message contains a task, event, deadline, or reminder that needs to be tracked
   Examples:
   - "remind me to submit assignment tomorrow"
   - "everyone should attend the meeting"
   - "don't forget the deadline is Friday"
   - "we have a test next week"
   - "need to call John at 3pm"
   - "meeting tomorrow at 5pm"

2. UPDATE - User wants to modify an existing reminder
   Examples:
   - "change the deadline to next week"
   - "reschedule the meeting to 4pm"
   - "update my reminder"

3. QUERY - User is asking about their reminders
   Examples:
   - "what's on my schedule?"
   - "when is the meeting?"
   - "show me my tasks"

4. CHITCHAT - Only use this for greetings, jokes, or completely unrelated messages
   Examples:
   - "hello"
   - "how are you?"
   - "lol that's funny"

IMPORTANT: If the message mentions ANY time-related information (tomorrow, today, deadline, meeting, event, task, etc.), classify it as NEW.

Message: "{message_text}"

Respond with ONLY a JSON object:
{{"intent": "NEW"}}

Intent must be one of: NEW, UPDATE, QUERY, CHITCHAT"""
    
    response = llm.invoke(prompt)
    
    # Log the raw response for debugging
    logger.info(f"Groq API responded successfully", extra={"node": "intent_node", "response_length": len(response.content)})
    logger.info(f"LLM Response: {response.content}", extra={"node": "intent_node"})
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response
        content = response.content.strip()
        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        intent = result.get("intent", "CHITCHAT")
        logger.info(f"Parsed intent from JSON: {intent}", extra={"node": "intent_node"})
    except Exception as e:
        logger.warning(f"Failed to parse JSON, using fallback: {e}", extra={"node": "intent_node", "response": response.content})
        # Fallback: Use keyword detection on the original message
        msg_lower = message_text.lower()
        
        # Check for NEW intent keywords (expanded list)
        new_keywords = [
            "remind", "schedule", "don't forget", "dont forget", "remember to", "need to",
            "have to", "must", "should", "gotta", "got to", "tomorrow", "today", "tonight",
            "deadline", "due", "meeting", "meet", "call", "attend", "submit", "assignment",
            "test", "exam", "project", "presentation", "event", "appointment", "task",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "next week", "this week", "by", "before", "until", "at", "pm", "am"
        ]
        
        if any(keyword in msg_lower for keyword in new_keywords):
            intent = "NEW"
        elif any(keyword in msg_lower for keyword in ["update", "change", "modify", "reschedule", "move"]):
            intent = "UPDATE"
        elif any(keyword in msg_lower for keyword in ["what", "when", "where", "show me", "list", "tell me"]):
            intent = "QUERY"
        else:
            intent = "CHITCHAT"
        logger.info(f"Fallback intent: {intent}", extra={"node": "intent_node"})
    
    state["intent"] = intent
    
    # Track metrics
    messages_processed.labels(intent=intent).inc()
    
    logger.info("Intent Node completed", extra={
        "node": "intent_node",
        "intent": intent
    })
    
    return state
