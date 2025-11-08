from typing import List
from src.shared.models import MessageDB, DeleteResponse
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class DeleteService:
    @staticmethod
    def delete_message(message_id: int, db: Session) -> DeleteResponse:
        message = db.query(MessageDB).filter(MessageDB.id == message_id).first()
        if not message:
            return DeleteResponse(deleted_count=0, message=f"Message with ID {message_id} not found")
        
        db.delete(message)
        db.commit()
        return DeleteResponse(deleted_count=1, message=f"Message {message_id} deleted successfully")

    @staticmethod
    def delete_multiple_messages(message_ids: List[int], db: Session) -> DeleteResponse:
        deleted_count = db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).count()
        db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).delete(synchronize_session=False)
        db.commit()
        
        return DeleteResponse(
            deleted_count=deleted_count,
            message=f"{deleted_count} message(s) deleted successfully"
        )