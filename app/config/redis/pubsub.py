import json

import redis.asyncio as aioredis

from .conn import redis_pool


class RedisPubSubManager:
    def __init__(self):
        self.client = None
        self.pubsub = None

    async def _get_redis_connection(self) -> aioredis.Redis:
        return aioredis.Redis(connection_pool=redis_pool, decode_responses=True, encoding="utf-8")

    async def connect(self):
        if not self.client:
            self.client = await self._get_redis_connection()

        if not self.pubsub:
            self.pubsub = self.client.pubsub()

    async def subscribe(self, channel: str) -> aioredis.Redis:
        await self.pubsub.subscribe(channel)
        return self.pubsub

    async def unsubscribe(self, channel: str):
        await self.pubsub.unsubscribe(channel)

    async def publish(self, channel: str, message: dict):
        """
        Publish a message to a Redis channel.

        :param channel: Redis channel name to publish the message to.
        :param message: Message to be published, should be a dictionary.
        """
        if not self.client:
            raise RuntimeError("Redis client is not connected.")
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary.")

        # Serialize the message to JSON
        message_json = json.dumps(message)

        # Publish the message to the specified channel
        await self.client.publish(channel, message_json)

    async def disconnect(self):
        if self.client:
            await self.client.close()


pubsub = RedisPubSubManager()

