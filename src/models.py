from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    seen = Column(Boolean, default=False, nullable=False)

# API Related Models
class MessageCreate(BaseModel):
    recipient_id: str = Field(..., description="Email of the message recipient")
    content: str = Field(..., min_length=1, description="Message content")

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_id: str
    content: str
    created_at: datetime
    seen: bool # no need to include this field when responding
    

class MessagesFetchResponse(BaseModel):
    messages: list[MessageResponse]
    count: int # count of messages returned

class DeleteMessagesRequest(BaseModel):
    message_ids: list[int] = Field(..., min_length=1, description="List of message IDs to delete")


class DeleteResponse(BaseModel):
    deleted_count: int
    message: str