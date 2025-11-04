from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    recipient_email: str = Field(..., description="Email of the message recipient")
    content: str = Field(..., min_length=1, description="Message content")
    sender_email: Optional[str] = Field(None, description="Optional sender email")
