from .models import MessageDB, MessageCreate, MessageResponse
from sqlalchemy.orm import Session

class MessageService:
    @staticmethod
    def create_message(message_create: MessageCreate, db: Session) -> MessageResponse:
        """Create a new message"""
        new_message = MessageDB(
            recipient_email=message_create.recipient_email,
            content=message_create.content,
            sender_email=message_create.sender_email
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        return MessageResponse.model_validate(new_message)