from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    sender_email = Column(String(255), nullable=True) # optional
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    seen = Column(Boolean, default=False, nullable=False)

# API Related Models
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
    seen: bool # no need to include this field when responding

    class Config:
        from_attributes = True

class MessagesFetchResponse(BaseModel):
    messages: list[MessageResponse]
    count: int # count of messages returned

class DeleteMessagesRequest(BaseModel):
    message_ids: list[int] = Field(..., min_items=1, description="List of message IDs to delete")


class DeleteResponse(BaseModel):
    deleted_count: int
    message: str