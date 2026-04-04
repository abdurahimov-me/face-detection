__all__ = (
    'redis_pool',
)

import redis.asyncio as aioredis

from ..settings import REDIS_SETTINGS


def create_redis_pool():
    return aioredis.ConnectionPool(
        host=REDIS_SETTINGS.REDIS_HOST, port=REDIS_SETTINGS.REDIS_PORT, db=REDIS_SETTINGS.REDIS_DB
    )


redis_pool = create_redis_pool()
