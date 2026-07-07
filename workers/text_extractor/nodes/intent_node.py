from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.metrics import messages_processed
import json
import re


# ---------------------------------------------------------------------------
# Fast pre-classification patterns (avoids LLM call for obvious cases)
# ---------------------------------------------------------------------------

_VENUE_PATTERNS = re.compile(
    r'\b(room|lab|block|wing|building|hall|venue|floor|esb|csb|apex|moved to|shifted to|changed to)\b',
    re.IGNORECASE
)

_SCHEDULE_CANCEL_PATTERNS = re.compile(
    r'\b(no class|cancelled|canceled|postponed|rescheduled|class off|lab off|no lab|no lecture)\b',
    re.IGNORECASE
)

_RESOURCE_PATTERNS = re.compile(
    r'\b(bring|carry|get your|collect|pick up|don\'t forget to bring|need to bring|submit your|fill (the |this )?form)\b',
    re.IGNORECASE
)


def _fast_precheck(text: str) -> str | None:
    """
    Quick regex-based pre-classification for high-confidence cases.
    Returns an intent string if confident, None if LLM should decide.
    """
    # Cancellations are high confidence — check first
    if _SCHEDULE_CANCEL_PATTERNS.search(text):
        return "SCHEDULE_CHANGE"

    # Venue changes (only if a location word AND a change word together)
    if _VENUE_PATTERNS.search(text) and re.search(
        r'\b(moved|shifted|changed|now in|will be in|is in|at)\b', text, re.IGNORECASE
    ):
        return "VENUE_CHANGE"

    # Resource callouts
    if _RESOURCE_PATTERNS.search(text):
        return "RESOURCE_CALLOUT"

    return None  # LLM decides


async def classify_intent(state: AgentState) -> AgentState:
    logger.info("Intent Node started", extra={
        "node": "intent_node",
        "message_text": state.get("message_text", "")[:100],
        "triage_signal": state.get("triage_signal", "unknown"),
    })

    message_text = state.get("message_text", "")

    # ---------------------------------------------------------------------------
    # Step 1: Fast pre-check (no LLM cost)
    # ---------------------------------------------------------------------------
    fast_intent = _fast_precheck(message_text)
    if fast_intent:
        logger.info(f"Fast pre-check matched intent: {fast_intent}", extra={"node": "intent_node"})
        state["intent"] = fast_intent
        messages_processed.labels(intent=fast_intent).inc()
        return state

    # ---------------------------------------------------------------------------
    # Step 2: LLM classification
    # ---------------------------------------------------------------------------
    from workers.text_extractor.core.config import settings
    if not settings.GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set!", extra={"node": "intent_node"})
        state["intent"] = "NEW"
        return state

    prompt = f"""You are an intent classifier for a university group chat reminder bot.
Classify the message below into exactly ONE of the following intents.

─────────────────────────────────────────────────────────────
INTENT DEFINITIONS
─────────────────────────────────────────────────────────────

NEW
  A new task, deadline, reminder, or event that needs to be tracked.
  Examples:
  - "Submit OS assignment by Friday 11pm"
  - "Lab test in CSE Lab 1 tomorrow"
  - "Bring OOPS record tomorrow"
  - "DSA lab today at 2pm"
  - "Next batch can come for USP"
  - "Math class at Apex 709"
  - "Write binary search and selection sort in record"
  - "Ma'am said we can collect tutorial sheets tomorrow"

UPDATE
  User wants to modify the deadline or details of an existing task.
  Examples:
  - "Deadline extended to Monday"
  - "Meeting rescheduled to 4pm"
  - "Change the submission to next week"

VENUE_CHANGE
  Location of a class, lab, or event has changed.
  Examples:
  - "Lab moved to ESB 509"
  - "Class shifted to room 304"
  - "Today's lecture is in block A hall"

SCHEDULE_CHANGE
  A class, lab, or event is cancelled, postponed, or rescheduled.
  Examples:
  - "No class tomorrow"
  - "Lab cancelled next week"
  - "Today's session postponed"

RESOURCE_CALLOUT
  Something needs to be brought, submitted, or collected.
  Examples:
  - "Bring your lab record tomorrow"
  - "Fill the Google form before 6pm"
  - "Collect attendance sheet from HOD office"

GROUP_ANNOUNCEMENT
  Important info for the whole group but no specific task or deadline.
  Examples:
  - "Internship drive results on portal"
  - "Next batch can come at 3pm for USP"
  - "Results are out on the notice board"

QUERY
  Someone is asking a question, no action needed.
  Examples:
  - "When is the test?"
  - "What's the deadline for the report?"

CHITCHAT
  Pure casual conversation with no actionable content.
  ONLY use this if the message has absolutely no relevance to any task,
  event, schedule, venue, or resource. When in doubt, use NEW.
  Examples:
  - "haha that's funny"
  - "what did you eat today"
  - "good morning everyone"

─────────────────────────────────────────────────────────────
CRITICAL RULES
─────────────────────────────────────────────────────────────
- If the message mentions a room, lab number, or block → prefer VENUE_CHANGE or NEW
- If the message mentions bringing something → prefer RESOURCE_CALLOUT or NEW
- If the message mentions a class/lab time without cancellation → prefer NEW or LAB_CALLOUT
- NEVER classify as CHITCHAT if there is any academic or work-related content
- When uncertain → use NEW (it's safer to over-classify than under-classify)

─────────────────────────────────────────────────────────────
Message: "{message_text}"
─────────────────────────────────────────────────────────────

Respond with ONLY a JSON object, nothing else:
{{"intent": "NEW", "confidence": 0.9, "reason": "one line explanation"}}

intent must be one of: NEW, UPDATE, VENUE_CHANGE, SCHEDULE_CHANGE, RESOURCE_CALLOUT, GROUP_ANNOUNCEMENT, QUERY, CHITCHAT"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        logger.info(f"LLM raw response: {content[:200]}", extra={"node": "intent_node"})

        # Strip markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        intent = result.get("intent", "CHITCHAT")
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "")

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
    """
    Keyword-based fallback when LLM fails.
    Errs on the side of NEW to avoid missing important messages.
    """
    msg = text.lower()

    if re.search(r'\b(no class|cancelled|canceled|postponed|rescheduled)\b', msg):
        return "SCHEDULE_CHANGE"

    if re.search(r'\b(moved to|shifted to|changed to|now in|room|block|wing|lab \d)\b', msg):
        return "VENUE_CHANGE"

    if re.search(r'\b(bring|collect|fill|pick up)\b', msg):
        return "RESOURCE_CALLOUT"

    if re.search(r'\b(update|change|modify|reschedule|extend|moved|deadline extended)\b', msg):
        return "UPDATE"

    if re.search(r'\b(what|when|where|show me|list|tell me|how many)\b', msg):
        return "QUERY"

    # Anything with academic or time content → NEW
    if re.search(
        r'\b(lab|test|exam|quiz|class|lecture|assignment|submit|deadline|due|tomorrow|today|friday|monday|tuesday|wednesday|thursday|saturday|sunday|record|report|project|presentation)\b',
        msg
    ):
        return "NEW"

    # Truly ambiguous — still use NEW (safer than CHITCHAT)
    return "CHITCHAT"
