from typing import TypedDict, Optional
from shared.schemas import EventExtraction

class AgentState(TypedDict):
    user_id: int
    group_id: Optional[int]
    message_text: str
    intent: Optional[str]
    db_context: Optional[str]
    extracted_data: Optional[EventExtraction]
    validation_error: Optional[str]
    needs_human: bool
    hitl_prompt: Optional[str]
