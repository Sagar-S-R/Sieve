from pydantic import BaseModel, Field
from typing import Optional

class EventExtraction(BaseModel):
    event_category: str = Field(description="The category of the event, e.g., 'meeting', 'deadline', 'task'.")
    title: str = Field(description="A short, descriptive title for the event or task.")
    action_required: str = Field(description="What needs to be done by the user.")
    deadline: Optional[str] = Field(default=None, description="The deadline for the task or event in ISO-8601 format.")
    confidence_score: float = Field(description="Confidence score from 0.0 to 1.0 of the extraction accuracy.")
    needs_clarification: bool = Field(description="True if crucial information like the deadline is missing or ambiguous.", default=False)
    
    # NEW FIELDS for redesign
    message_type: str = Field(default="deadline", description="Type of message: deadline, announcement, form_deadline")
    applies_at: Optional[str] = Field(default=None, description="When the event happens (class time, meeting time) in ISO-8601 format. Different from deadline.")
    location: Optional[str] = Field(default=None, description="Venue, room, lab, block where the event happens.")
    form_url: Optional[str] = Field(default=None, description="Google Form or other URL if this is a form submission task.")
    reminder_strategy: str = Field(default="standard", description="Reminder strategy: standard (24h, 1h, deadline) | morning_of (8am day-of) | immediate (DM right away)")
    match_confidence: Optional[float] = Field(default=None, description="For UPDATE intent: confidence that we matched the right existing task (0.0-1.0).")
