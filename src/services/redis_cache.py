import redis.asyncio as redis
from typing import Any, Optional, TypeVar, Dict, Tuple
from src.core.config import settings
from src.core.logging import get_logger


T = TypeVar('T')
logger = get_logger(__name__)

class AsyncRedisCache:
    def __init__(self):
        self.redis_client = None
        
    async def init(self):
        """Initialize Redis connection pool"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        
    async def close(self):
        """Close Redis connection pool"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            
    async def health_check(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Redis connection is healthy.
        
        Returns:
            Tuple of (is_healthy, error_message)
        """
        try:
            await self.init()
            # Simple ping-pong test to verify Redis is responding
            response = await self.redis_client.ping()
            if response:
                return True, None
            return False, "Redis ping failed"
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}", exc_info=True)
            return False, str(e)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache by key"""
        try:
            await self.init()
            logger.info(f"Getting cache for key: {key}")
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis get operation failed for key {key}: {str(e)}")
            # Graceful degradation - continue without cache
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL (in seconds)"""
        try:
            await self.init()
            if ttl is None:
                ttl = settings.CACHE_TTL
            
            logger.info(f"Setting cache for key: {key} with TTL: {ttl}")
            return await self.redis_client.set(key, value, ex=ttl)
        except Exception as e:
            logger.error(f"Redis set operation failed for key {key}: {str(e)}")
            # Graceful degradation - continue without cache
            return False
    
    async def delete(self, key: str) -> int:
        """Delete a key from cache"""
        await self.init()
        return await self.redis_client.delete(key)
    
    def generate_key(self, base: str, *args) -> str:
        """Generate a cache key from base and arguments"""
        return f"{base}:{':'.join(str(arg) for arg in args)}"

# Create a singleton instance
cache = AsyncRedisCache()