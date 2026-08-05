from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from shared.metrics import messages_processed
import json
import re


async def classify_intent(state: AgentState) -> AgentState:
    logger.info("Intent Node started", extra={
        "node": "intent_node",
        "message_text": state.get("message_text", "")[:100],
        "triage_signal": state.get("triage_signal", "unknown"),
    })

    message_text = state.get("message_text", "")

    from workers.text_extractor.core.config import settings
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set!", extra={"node": "intent_node"})
        state["intent"] = "NEW"
        return state

    prompt = f"""You are an intent classifier for a university group chat reminder bot.
Classify the message below into exactly ONE of the following 5 intents.

INTENT DEFINITIONS

NEW
  A new task, deadline, reminder, or event that needs to be tracked.
  This includes venue changes, cancellations, resource callouts — anything the group needs to act on.
  Examples:
  - "Submit OS assignment by Friday 11pm"
  - "Lab moved to ESB 509 tomorrow"
  - "No class today"
  - "Bring your lab record tomorrow"
  - "DSA lab today at 2pm"
  - "Math class at Apex 709"

UPDATE
  User wants to modify the deadline or details of an EXISTING already-tracked task.
  Examples:
  - "Deadline extended to Monday"
  - "Meeting rescheduled to 4pm"
  - "Change the OS submission to next week"

ANNOUNCEMENT
  General group info with no specific deadline or action required.
  Something the group should know, but nothing to track or remind.
  Examples:
  - "Internship drive results are on the portal"
  - "Results are out on the notice board"
  - "HOD meeting went well"

FORM_DEADLINE
  A Google Form or external link with a submission deadline.
  Examples:
  - "Fill this form by tonight: forms.gle/abc123"
  - "Register here before Friday: bit.ly/xyz"

CHITCHAT
  Everything else — questions, reactions, casual conversation.
  If it is not actionable and does not need to be tracked, it is CHITCHAT.
  Examples:
  - "When is the test?"
  - "haha okay"
  - "good morning"

CRITICAL RULES
- Venue changes, cancellations, resource callouts → NEW
- Google Form with a deadline → FORM_DEADLINE
- Modifying something already saved → UPDATE
- Pure questions or reactions → CHITCHAT
- When uncertain → use NEW (safer to over-classify than under-classify)

Message: "{message_text}"

Respond with ONLY a JSON object, nothing else:
{{"intent": "NEW", "confidence": 0.9, "reason": "one line explanation"}}

intent must be one of: NEW, UPDATE, ANNOUNCEMENT, FORM_DEADLINE, CHITCHAT"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        logger.info(f"LLM raw response: {content[:200]}", extra={"node": "intent_node"})

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        intent = result.get("intent", "CHITCHAT")
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "")

        # Safety net: map any old rogue intents to correct ones
        _ROGUE_MAP = {
            "VENUE_CHANGE": "NEW",
            "SCHEDULE_CHANGE": "NEW",
            "RESOURCE_CALLOUT": "NEW",
            "GROUP_ANNOUNCEMENT": "ANNOUNCEMENT",
            "QUERY": "CHITCHAT",
        }
        intent = _ROGUE_MAP.get(intent, intent)

        logger.info(f"LLM intent: {intent} (confidence={confidence}) | {reason}", extra={"node": "intent_node"})

    except Exception as e:
        logger.warning(f"LLM parse failed, using fallback: {e}", extra={"node": "intent_node"})
        intent = _keyword_fallback(message_text)
        logger.info(f"Fallback intent: {intent}", extra={"node": "intent_node"})

    state["intent"] = intent
    messages_processed.labels(intent=intent).inc()

    logger.info("Intent Node completed", extra={"node": "intent_node", "intent": intent})
    return state


def _keyword_fallback(text: str) -> str:
    """Keyword-based fallback when LLM fails. Errs on the side of NEW."""
    msg = text.lower()

    if re.search(r'\b(update|change|modify|reschedule|extend|deadline extended)\b', msg):
        return "UPDATE"

    if re.search(r'forms\.gle|bit\.ly|tinyurl|fill.*form|form.*link', msg):
        return "FORM_DEADLINE"

    if re.search(r'\b(internship|results|portal|notice board)\b', msg) and not re.search(
        r'\b(deadline|due|submit|bring|tomorrow|today)\b', msg
    ):
        return "ANNOUNCEMENT"

    if re.search(
        r'\b(lab|test|exam|quiz|class|lecture|assignment|submit|deadline|due|tomorrow|today|'
        r'friday|monday|tuesday|wednesday|thursday|saturday|sunday|record|report|project|'
        r'presentation|bring|no class|cancelled|room|venue|moved|shifted)\b',
        msg
    ):
        return "NEW"

    return "CHITCHAT"
