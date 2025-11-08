import json
import logging
from typing import List, Optional, Dict, Any
import redis.asyncio as redis
from src.shared.models import MessageResponse
import os

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.aclose()  # Use aclose() instead of close()
            logger.info("Redis connection closed")
    
    # Rest of the methods remain the same...
    def _get_new_messages_key(self, recipient_id: str) -> str:
        """Get Redis key for new messages of a recipient"""
        return f"new_messages:{recipient_id}"
    
    def _get_message_key(self, message_id: int) -> str:
        """Get Redis key for a specific message"""
        return f"message:{message_id}"
    
    async def cache_new_message(self, message: MessageResponse):
        """Cache a new message for a recipient"""
        try:
            if not self.redis:
                return
            
            # Add to recipient's new messages list (as sorted set with timestamp)
            key = self._get_new_messages_key(message.recipient_id)
            message_data = {
                "id": message.id,
                "recipient_id": message.recipient_id,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "seen": message.seen
            }
            
            # Use message ID as score for ordering
            await self.redis.zadd(key, {json.dumps(message_data): message.id})
            
            # Cache individual message
            message_key = self._get_message_key(message.id)
            await self.redis.setex(message_key, 3600, json.dumps(message_data))  # 1 hour TTL
            
            logger.info(f"Cached new message {message.id} for recipient {message.recipient_id}")
            
        except Exception as e:
            logger.error(f"Error caching new message: {e}")
    
    async def get_new_messages(self, recipient_id: str) -> List[MessageResponse]:
        """Get new messages for a recipient from cache"""
        try:
            if not self.redis:
                return []
            
            key = self._get_new_messages_key(recipient_id)
            
            # Get all messages from sorted set (ordered by message ID)
            cached_messages = await self.redis.zrange(key, 0, -1)
            
            if not cached_messages:
                return []
            
            messages = []
            for msg_json in cached_messages:
                try:
                    msg_data = json.loads(msg_json)
                    # Convert back to MessageResponse
                    from datetime import datetime
                    msg_data['created_at'] = datetime.fromisoformat(msg_data['created_at'])
                    messages.append(MessageResponse(**msg_data))
                except Exception as e:
                    logger.error(f"Error deserializing cached message: {e}")
            
            logger.info(f"Retrieved {len(messages)} cached new messages for recipient {recipient_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error getting cached new messages: {e}")
            return []
    
    async def mark_messages_as_seen(self, recipient_id: str, message_ids: List[int]):
        """Remove messages from new messages cache (mark as seen)"""
        try:
            if not self.redis or not message_ids:
                return
            
            key = self._get_new_messages_key(recipient_id)
            
            # Get all cached messages
            cached_messages = await self.redis.zrange(key, 0, -1)
            
            # Remove messages that were fetched
            for msg_json in cached_messages:
                try:
                    msg_data = json.loads(msg_json)
                    if msg_data['id'] in message_ids:
                        await self.redis.zrem(key, msg_json)
                except Exception as e:
                    logger.error(f"Error removing message from cache: {e}")
            
            logger.info(f"Marked {len(message_ids)} messages as seen for recipient {recipient_id}")
            
        except Exception as e:
            logger.error(f"Error marking messages as seen in cache: {e}")
    
    async def delete_message_from_cache(self, message_id: int, recipient_id: str):
        """Delete a message from all caches"""
        try:
            if not self.redis:
                return
            
            # Remove from individual message cache
            message_key = self._get_message_key(message_id)
            await self.redis.delete(message_key)
            
            # Remove from new messages cache
            key = self._get_new_messages_key(recipient_id)
            cached_messages = await self.redis.zrange(key, 0, -1)
            
            for msg_json in cached_messages:
                try:
                    msg_data = json.loads(msg_json)
                    if msg_data['id'] == message_id:
                        await self.redis.zrem(key, msg_json)
                        break
                except Exception as e:
                    logger.error(f"Error removing deleted message from cache: {e}")
            
            logger.info(f"Deleted message {message_id} from cache")
            
        except Exception as e:
            logger.error(f"Error deleting message from cache: {e}")
    
    async def clear_recipient_cache(self, recipient_id: str):
        """Clear all cached messages for a recipient"""
        try:
            if not self.redis:
                return
            
            key = self._get_new_messages_key(recipient_id)
            await self.redis.delete(key)
            
            logger.info(f"Cleared cache for recipient {recipient_id}")
            
        except Exception as e:
            logger.error(f"Error clearing recipient cache: {e}")

# Global cache instance
redis_cache = RedisCache()