from typing import List
from src.shared.models import MessageDB, DeleteResponse
from src.shared.redis import redis_cache
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class DeleteService:
    @staticmethod
    async def delete_message(message_id: int, db: Session) -> DeleteResponse:
        try:
            # Get message details before deletion (for cache cleanup)
            message = db.query(MessageDB).filter(MessageDB.id == message_id).first()
            if not message:
                return DeleteResponse(deleted_count=0, message=f"Message with ID {message_id} not found")
            
            recipient_id = message.recipient_id
            
            # Delete from database
            db.delete(message)
            db.commit()
            
            # Remove from cache
            await redis_cache.delete_message_from_cache(message_id, recipient_id)
            
            return DeleteResponse(deleted_count=1, message=f"Message {message_id} deleted successfully")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting message: {e}")
            raise

    @staticmethod
    async def delete_multiple_messages(message_ids: List[int], db: Session) -> DeleteResponse:
        try:
            # Get message details before deletion (for cache cleanup)
            messages = db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).all()
            recipient_message_map = {}
            for msg in messages:
                if msg.recipient_id not in recipient_message_map:
                    recipient_message_map[msg.recipient_id] = []
                recipient_message_map[msg.recipient_id].append(msg.id)
            
            # Delete from database
            deleted_count = db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).count()
            db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).delete(synchronize_session=False)
            db.commit()
            
            # Remove from cache
            for recipient_id, msg_ids in recipient_message_map.items():
                for msg_id in msg_ids:
                    await redis_cache.delete_message_from_cache(msg_id, recipient_id)
            
            return DeleteResponse(
                deleted_count=deleted_count,
                message=f"{deleted_count} message(s) deleted successfully"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting messages: {e}")
            raise