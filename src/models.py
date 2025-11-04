from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    recipient_email: str = Field(..., description="Email of the message recipient")
    content: str = Field(..., min_length=1, description="Message content")
    sender_email: Optional[str] = Field(None, description="Optional sender email")

class MessageResponse(BaseModel):
    id: int
    recipient_email: str
    content: str
    sender_email: Optional[str]
    created_at: datetime
    is_fetched: bool