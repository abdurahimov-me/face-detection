__all__ = (
    'cache',
    'AsyncRedisCache',
)

import json
import logging
from datetime import timedelta
from typing import Optional, Union, Dict

import redis.asyncio as redis

from .conn import redis_pool

logger = logging.getLogger(__name__)


class AsyncRedisCache:
    ENCODE_BOOL_TYPES = {
        True: 'true',
        False: 'false',
    }
    DECODE_BOOL_TYPES = {
        'true': True,
        'false': False,
    }

    def __init__(self, pool):
        self.client: redis.Redis = redis.Redis(connection_pool=pool, decode_responses=True)
        self.pool = pool

    async def clear(self):
        """
        Dangerous method to clear all cached data.
        :return:ø
        """

        await self.client.flushall()

    async def set(self, key: str, value: Union[str, Dict], expire: Union[int, timedelta] = timedelta(hours=1)) -> bool:
        """
        Store a key-value pair in Redis.

        :param key: The key name
        :param value: The value to store (str or dict)
        :param expire: Expiration time in seconds, default is 1 hour
        :return: True if successfully stored, otherwise False
        """
        try:

            if isinstance(value, bool):
                value = self.ENCODE_BOOL_TYPES[value]
            elif isinstance(value, str):
                value = value
            else:
                if value is None:
                    return True
                value = json.dumps(value)

            expire = expire if isinstance(expire, int) else int(expire.total_seconds() // 1)

            await self.client.set(name=key, value=value, ex=expire)
            return True

        except redis.RedisError as e:
            logger.error(f"Error setting value in Redis: {e}")
            return False

    async def get(self, key: str) -> Optional[Union[str, Dict]]:
        """
        Retrieve a value from Redis.

        :param key: The key name
        :return: The value corresponding to the key (str or dict) or None if not found
        """
        try:
            value = await self.client.get(name=key)

            if isinstance(value, bytes):
                value = value.decode('utf-8')

            if value is not None:
                if value in self.DECODE_BOOL_TYPES:
                    return self.DECODE_BOOL_TYPES[value]
                try:
                    return json.loads(value)  # Convert to dict if value is JSON
                except json.JSONDecodeError:
                    return value  # Return as string if not JSON
            return None
        except redis.RedisError as e:
            logger.error(f"Error retrieving value in Redis: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete a key-value pair from Redis.

        :param key: The key name
        :return: True if successfully deleted, otherwise False
        """
        try:
            result = await self.client.delete(key)
            return result > 0  # Redis returns the number of keys deleted
        except redis.RedisError as e:
            print(f"Error deleting key from Redis: {e}")
            return False

    async def incr(self, key: str, value) -> int:
        return await self.client.incr(key, value)

    async def lpush(self, name, value):
        return await self.client.lpush(name, value)

    async def expire(self, key: str, ex: int) -> int:
        return await self.client.expire(key, ex)


cache = AsyncRedisCache(pool=redis_pool)
