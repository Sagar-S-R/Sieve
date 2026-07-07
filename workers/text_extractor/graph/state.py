from typing import TypedDict, Optional, List
from shared.schemas import EventExtraction


class AgentState(TypedDict):
    # Core message info
    user_id: int
    group_id: Optional[int]
    message_text: str
    triage_signal: Optional[str]        # "high_signal" | "low_signal" (from triage)

    # Intent classification
    # NEW, UPDATE, CORRECTION, CHITCHAT, QUERY,
    # VENUE_CHANGE, LAB_CALLOUT, SCHEDULE_CHANGE, RESOURCE_CALLOUT, GROUP_ANNOUNCEMENT
    intent: Optional[str]

    # NEW: Rolling message buffer and agentic context
    message_buffer: Optional[List[str]]  # Last 20 raw messages from this group
    db_context: Optional[str]  # Context fetched from DB (based on LLM decision)
    context_retrieval_reasoning: Optional[str]  # Why the LLM chose this context

    # LangGraph pipeline state
    extracted_data: Optional[EventExtraction]
    validation_error: Optional[str]
    needs_human: bool
    hitl_prompt: Optional[str]

    # Update / correction flow with confirmation
    is_update: Optional[bool]
    update_candidates: Optional[List[dict]]  # List of potential matching tasks
    selected_task_id: Optional[int]  # Task ID user confirmed to update
    updating_task_title: Optional[str]

    # New intent payloads
    venue_info: Optional[dict]           # {old_venue, new_venue, task_title}
    schedule_change_info: Optional[dict] # {change_type: "cancelled"|"postponed", target}
    announcement_text: Optional[str]     # For GROUP_ANNOUNCEMENT forwarding
