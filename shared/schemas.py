from pydantic import BaseModel, Field
from typing import Optional

class EventExtraction(BaseModel):
    event_category: str = Field(description="The category of the event, e.g., 'meeting', 'deadline', 'task'.")
    title: str = Field(description="A short, descriptive title for the event or task.")
    action_required: str = Field(description="What needs to be done by the user.")
    deadline: Optional[str] = Field(default=None, description="The deadline for the task or event in ISO-8601 format.")
    confidence_score: float = Field(description="Confidence score from 0.0 to 1.0 of the extraction accuracy.")
    needs_clarification: bool = Field(description="True if crucial information like the deadline is missing or ambiguous.", default=False)
