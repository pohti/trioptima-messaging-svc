from .models import MessageDB, MessageCreate, MessageResponse, DeleteResponse
from sqlalchemy.orm import Session

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
    
    # fetch new messages

    @staticmethod
    def delete_message(message_id: int, db: Session) -> DeleteResponse:
        message = db.query(MessageDB).filter(MessageDB.id == message_id).first()
        if not message:
            return DeleteResponse(deleted_count=0, message=f"Message with ID {message_id} not found")
        
        db.delete(message)
        db.commit()
        return DeleteResponse(deleted_count=1, message=f"Message {message_id} deleted successfully")
