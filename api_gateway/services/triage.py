"""
Message triage service.

Two-stage triage for group chat messages:
  Stage 1 - Pure noise check: drop obviously irrelevant one-word/emoji responses.
  Stage 2 - Priority tagging: label remaining messages high_signal vs low_signal.
"""

import re


# Stage 1 - Pure noise patterns (must match the ENTIRE message via re.fullmatch)
_PURE_NOISE_PATTERNS = [
    r'^[\U0001F44D\U0001F44E\U0001F602\U0001F64F\u2764\u2705\U0001F525\U0001F480\U0001F44C\U0001F44B\U0001F64C\U0001F44F]+$',
    r'^(ok|okay|k|yes|no|yep|nope|nah|same|real|lol|haha|hehe|hmm|oh|ah|gg|bruh|lmao|lmfao|omg|wtf|fr|ngl|imo|smh)$',
    r'^(thanks|thank you|ty|np|noted|sure|fine|got it|ic|ik|gotcha|roger|copy that|understood|alright|alr)$',
    r'^(nice|great|good|cool|wow|damn|bro|dude|man|yaar|bhai|ok bro|ok thanks|okay thanks)$',
]

_COMPILED_NOISE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PURE_NOISE_PATTERNS]

# Stage 2 - High signal keywords for priority tagging
_HIGH_SIGNAL_KEYWORDS = [
    "deadline", "due", "submit", "submission", "by", "before", "until",
    "tomorrow", "today", "tonight", "eod", "cob",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "lab", "test", "exam", "quiz", "assignment", "homework", "project",
    "report", "presentation", "record", "practical", "practicum",
    "viva", "hackathon", "internship", "placement",
    "room", "venue", "block", "wing", "building", "hall", "floor",
    "moved", "shifted", "changed", "cancelled", "postponed", "rescheduled",
    "bring", "write", "fill", "collect", "attend", "join", "register",
    "meeting", "class", "lecture", "session", "seminar", "workshop",
]


def is_pure_noise(message: str) -> bool:
    """
    Stage 1 triage: Returns True ONLY for messages that are obviously noise.

    Safety rules - never drop if:
    - Message is longer than 5 words
    - Contains any digit
    - Contains a URL
    - Contains a hashtag or @ mention
    """
    msg = message.strip().lower()

    if not msg:
        return True

    if len(msg.split()) > 5:
        return False

    if any(char.isdigit() for char in msg):
        return False

    if 'http' in msg or 'www.' in msg:
        return False

    if '#' in msg or '@' in msg:
        return False

    return any(p.fullmatch(msg) for p in _COMPILED_NOISE_PATTERNS)


def triage_message(text: str) -> tuple[bool, str]:
    """
    Two-stage triage. Returns (should_drop, reason).

    Returns:
        (True,  "noise")        -> drop, do not queue
        (False, "high_signal")  -> queue with priority flag
        (False, "low_signal")   -> queue normally
    """
    if is_pure_noise(text):
        return (True, "noise")

    text_lower = text.lower()
    has_high_signal = any(kw in text_lower for kw in _HIGH_SIGNAL_KEYWORDS)
    return (False, "high_signal") if has_high_signal else (False, "low_signal")
