from typing import List
from src.shared.models import (
    MessageDB, 
    MessageResponse,
    MessagesFetchResponse,
    DeleteResponse
)
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)

class ReaderService:
    @staticmethod
    def fetch_new_messages(recipient_id: str, db: Session) -> MessagesFetchResponse:
        try:
            # Use FOR UPDATE to lock rows atomically
            # This prevents other transactions from seeing these rows until we commit
            new_messages = db.query(MessageDB).filter(
                and_(
                    MessageDB.recipient_id == recipient_id,
                    MessageDB.seen == False
                )
            ).order_by(MessageDB.created_at.asc()).with_for_update().all()

            # mark messages as seen within the same transaction
            if new_messages:
                for message in new_messages:
                    message.seen = True
                db.commit()  # Commit the transaction atomically
            else:
                db.commit()  # Commit empty transaction

            # no need to show 'seen' field in response
            return MessagesFetchResponse(
                messages=[MessageResponse.model_validate(msg) for msg in new_messages],
                count=len(new_messages)
            )
            
        except Exception as e:
            db.rollback()  # Rollback on any error
            logger.error(f"Error fetching new messages atomically: {e}")
            raise

    @staticmethod
    def fetch_messages_by_index(
        recipient_id: str,
        start_index: int,
        stop_index: int,
        db: Session
    ) -> MessagesFetchResponse:
        try:
            # Use FOR UPDATE to lock rows atomically
            messages = db.query(MessageDB).filter(
                and_(
                    MessageDB.recipient_id == recipient_id,
                    MessageDB.id >= start_index,
                    MessageDB.id <= stop_index
                )
            ).order_by(MessageDB.id.asc()).with_for_update().all()
            
            # update all fetched messages as seen within the same transaction
            if messages:
                for message in messages:
                    message.seen = True
                db.commit()  # Commit the transaction atomically
            else:
                db.commit()  # Commit empty transaction

            return MessagesFetchResponse(
                messages=[MessageResponse.model_validate(msg) for msg in messages],
                count=len(messages),
            )
            
        except Exception as e:
            db.rollback()  # Rollback on any error
            logger.error(f"Error fetching messages by index atomically: {e}")
            raise

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