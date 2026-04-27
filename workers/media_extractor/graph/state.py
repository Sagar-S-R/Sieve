from typing import TypedDict, Optional
from shared.schemas import EventExtraction


class AgentState(TypedDict):
    user_id: int
    group_id: Optional[int]
    file_id: str
    file_path: Optional[str]
    media_type: str  # 'image' or 'pdf'
    raw_text: Optional[str]
    extracted_data: Optional[EventExtraction]
    validation_error: Optional[str]
    needs_human: bool
    hitl_prompt: Optional[str]
