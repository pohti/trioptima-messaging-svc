from typing import List
from src.shared.models import (
    MessageDB, 
    MessageCreateReq, 
    MessageResponse,
    MessagesFetchResponse,
    DeleteResponse
)
from src.shared.rabbit_mq import rabbitmq_manager
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)

class MessageService:
    MESSAGE_QUEUE = "message_processing_queue"
    
    @staticmethod
    async def queue_message(message_create_req: MessageCreateReq) -> dict:
        """Queue a message for async processing"""
        try:
            message_data = {
                "recipient_id": message_create_req.recipient_id,
                "content": message_create_req.content,
            }
            
            # Ensure RabbitMQ connection
            if not rabbitmq_manager.connection:
                await rabbitmq_manager.connect()
            
            # Declare queue if not exists
            await rabbitmq_manager.declare_queue(MessageService.MESSAGE_QUEUE)
            
            # Publish message to queue
            await rabbitmq_manager.publish_message(
                MessageService.MESSAGE_QUEUE, 
                message_data
            )
            
            logger.info(f"Message queued successfully for recipient {message_create_req.recipient_id}")
            return {
                "status": "queued",
                "message": "Message has been queued for processing",
                "recipient_id": message_create_req.recipient_id
            }
            
        except Exception as e:
            logger.error(f"Failed to queue message: {e}")
            raise
    
    @staticmethod
    def create_message(message_create_req: MessageCreateReq, db: Session) -> MessageResponse:
        """Direct synchronous message creation (kept for backward compatibility)"""
        new_message = MessageDB(
            recipient_id=message_create_req.recipient_id,
            content=message_create_req.content,
        )
        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        return MessageResponse.model_validate(new_message)
    
    @staticmethod
    def fetch_new_messages(recipient_id: str, db: Session) -> MessagesFetchResponse:
        # filter new messages
        new_messages = db.query(MessageDB).filter(
            and_(
                MessageDB.recipient_id == recipient_id,
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

        # no need to show 'seen' field in response
        return MessagesFetchResponse(
            messages=[MessageResponse.model_validate(msg) for msg in new_messages],
            count=len(new_messages)
        )

    @staticmethod
    def fetch_messages_by_index(
        recipient_id: str,
        start_index: int,
        stop_index: int,
        db: Session
    ) -> MessagesFetchResponse:
        # filter for messages by start_index <= id <= stop_index
        messages = db.query(MessageDB).filter(
            and_(
                MessageDB.recipient_id == recipient_id,
                MessageDB.id >= start_index,
                MessageDB.id <= stop_index
            )
        ).order_by(MessageDB.id.asc()).all() # improvement: allow ordering by desc as well
        
        # update all fetched messages as seen
        if messages:
            message_ids = [msg.id for msg in messages]
            db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).update(
                {MessageDB.seen: True}, synchronize_session=False
            )
            db.commit()

        return MessagesFetchResponse(
            messages=[MessageResponse.model_validate(msg) for msg in messages],
            count=len(messages),
        )

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