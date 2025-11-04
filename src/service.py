from .models import (
    MessageDB, 
    MessageCreate, 
    MessageResponse,
    MessagesFetchResponse,
    DeleteResponse
)
from sqlalchemy.orm import Session
from sqlalchemy import and_

class MessageService:
    @staticmethod
    def create_message(message_create: MessageCreate, db: Session) -> MessageResponse:
        new_message = MessageDB(
            recipient_email=message_create.recipient_email,
            content=message_create.content,
            sender_email=message_create.sender_email
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        return MessageResponse.model_validate(new_message)
    
    @staticmethod
    def fetch_new_messages(recipient_email: str, db: Session) -> MessagesFetchResponse:
        # filter new messages
        new_messages = db.query(MessageDB).filter(
            and_(
                MessageDB.recipient_email == recipient_email,
                MessageDB.seen == False
            )
        ).order_by(MessageDB.created_at.asc()).all()

        # mark messages as seen
        if new_messages:
            message_ids = [msg.id for msg in new_messages]
            db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).update(
                {MessageDB.seen: True}, synchronize_session=False
            )
            db.commit()

        total_count = db.query(MessageDB).filter(MessageDB.recipient_email == recipient_email).count()

        # no need to show 'seen' field in response
        return MessagesFetchResponse(
            messages=[MessageResponse.model_validate(msg) for msg in new_messages],
            total_count=total_count
        )


    @staticmethod
    def delete_message(message_id: int, db: Session) -> DeleteResponse:
        message = db.query(MessageDB).filter(MessageDB.id == message_id).first()
        if not message:
            return DeleteResponse(deleted_count=0, message=f"Message with ID {message_id} not found")
        
        db.delete(message)
        db.commit()
        return DeleteResponse(deleted_count=1, message=f"Message {message_id} deleted successfully")
