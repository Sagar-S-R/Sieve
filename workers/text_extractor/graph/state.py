from typing import TypedDict, Optional, List
from shared.schemas import EventExtraction


class AgentState(TypedDict):
    # Core
    user_id: int
    group_id: Optional[int]
    message_text: str
    original_message: Optional[str]
    is_personal: bool                        # True for private DM tasks, False for group

    # Intent
    intent: Optional[str]
    triage_signal: Optional[str]

    # Context
    message_buffer: Optional[List[str]]
    db_context: Optional[str]
    context_retrieval_reasoning: Optional[str]

    # Extraction
    extracted_data: Optional[EventExtraction]

    # Update flow
    update_candidates: Optional[List[dict]]
    excluded_task_ids: Optional[List[int]]
    selected_task_id: Optional[int]
    updating_task_title: Optional[str]

    # HITL
    needs_human: bool
    hitl_reason: Optional[str]
    hitl_prompt: Optional[str]
    hitl_round: int

    # Validation
    validation_error: Optional[str]

    # Legacy payloads (group intents)
    is_update: Optional[bool]
    venue_info: Optional[dict]
    schedule_change_info: Optional[dict]
    announcement_text: Optional[str]
