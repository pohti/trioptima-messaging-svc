from typing import List
from src.shared.models import (
    MessageDB, 
    MessageResponse,
    MessagesFetchResponse,
)
from src.shared.redis import redis_cache
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)

class ReaderService:
    @staticmethod
    async def fetch_new_messages(recipient_id: str, db: Session) -> MessagesFetchResponse:
        """Fetch new messages with cache-first strategy"""
        try:
            # 1. Try to get from cache first
            cached_messages = await redis_cache.get_new_messages(recipient_id)
            
            if cached_messages:
                # Mark cached messages as seen in cache
                message_ids = [msg.id for msg in cached_messages]
                await redis_cache.mark_messages_as_seen(recipient_id, message_ids)
                
                # Also mark as seen in database for consistency
                if message_ids:
                    db.query(MessageDB).filter(MessageDB.id.in_(message_ids)).update(
                        {MessageDB.seen: True}, synchronize_session=False
                    )
                    db.commit()
                
                logger.info(f"Served {len(cached_messages)} messages from cache for {recipient_id}")
                return MessagesFetchResponse(
                    messages=cached_messages,
                    count=len(cached_messages)
                )
            
            # 2. Fallback to database if cache miss
            logger.info(f"Cache miss for {recipient_id}, falling back to database")
            
            # Use FOR UPDATE to lock rows atomically
            new_messages = db.query(MessageDB).filter(
                and_(
                    MessageDB.recipient_id == recipient_id,
                    MessageDB.seen == False
                )
            ).order_by(MessageDB.created_at.asc()).with_for_update().all()

            # Mark messages as seen within the same transaction
            if new_messages:
                for message in new_messages:
                    message.seen = True
                db.commit()
            else:
                db.commit()

            # Convert to response models
            response_messages = [MessageResponse.model_validate(msg) for msg in new_messages]
            
            return MessagesFetchResponse(
                messages=response_messages,
                count=len(response_messages)
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error fetching new messages: {e}")
            raise

    @staticmethod
    def fetch_messages_by_index(
        recipient_id: str,
        start_index: int,
        stop_index: int,
        db: Session
    ) -> MessagesFetchResponse:
        """Fetch messages by index (no caching for this endpoint)"""
        try:
            # Use FOR UPDATE to lock rows atomically
            messages = db.query(MessageDB).filter(
                and_(
                    MessageDB.recipient_id == recipient_id,
                    MessageDB.id >= start_index,
                    MessageDB.id <= stop_index
                )
            ).order_by(MessageDB.id.asc()).with_for_update().all()
            
            # Update all fetched messages as seen within the same transaction
            if messages:
                for message in messages:
                    message.seen = True
                db.commit()
            else:
                db.commit()

            return MessagesFetchResponse(
                messages=[MessageResponse.model_validate(msg) for msg in messages],
                count=len(messages),
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error fetching messages by index: {e}")
            raise