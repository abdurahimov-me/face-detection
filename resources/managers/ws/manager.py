import asyncio
import json
import logging
from typing import Iterable
from uuid import uuid4

from fastapi import WebSocket

from config.redis import cache
from config.redis.pubsub import pubsub as pubsub_redis
from resources.managers.ws.connections import connections

logger = logging.getLogger(__name__)


class ChatWebSocketManager:
    def __init__(self, pubsub=pubsub_redis):
        self.worker_id: str = str(uuid4())[-4:]
        self.handlers: dict = {}
        self.tasks = []
        self.pubsub = pubsub

    def handler(self, message_type):
        def decorator(func):
            self.handlers[message_type] = func
            return func

        return decorator

    async def start(self):
        await self.pubsub.connect()

        if workers := await cache.get('workers'):
            workers.append(self.worker_id)
        else:
            workers = [self.worker_id]
        await cache.set('workers', workers)
        self.tasks.append(asyncio.create_task(self._pubsub_data_reader()))

    async def stop(self):
        if self.pubsub:
            await self.pubsub.disconnect()
        for task in self.tasks:
            task.cancel()

    async def connect(self, conn_id: str, websocket: WebSocket):
        await websocket.accept()
        await cache.client.hset('user_connections', conn_id, self.worker_id)
        connections.add(conn_id, websocket)

    async def disconnect(self, conn_id):
        await cache.client.hdel('user_connections', conn_id)
        connections.remove(conn_id)

    async def send_all_conns(self, data: dict):
        workers = await cache.get('workers') or []
        new_data = dict(data=data, key='send_all')
        for worker in workers:
            if workers != self.worker_id:
                await self.publish_to_worker(data=new_data, worker_id=worker)
            else:
                await connections.send_all(data=data)

    async def send_broadcast(self, conn_ids: Iterable, data: dict, ):
        await asyncio.gather(
            *[self.send_msg(conn_id, data) for conn_id in conn_ids]
        )

    async def publish_to_worker(self, data: dict, worker_id: str):
        await self.pubsub.publish(f"worker:{worker_id}", data)

    async def send_msg(self, conn_id, data: dict):
        """Send a message to a user's WebSocket connection."""
        conn_id = str(conn_id)
        if websocket := connections.get(conn_id):
            # If the WebSocket is in this worker
            await websocket.send_json(data)
        else:
            worker_id = await cache.client.hget("user_connections", conn_id)
            data = dict(data=data, conn_id=conn_id, key='conn_id')
            if worker_id:
                await self.publish_to_worker(data=data, worker_id=worker_id.decode('utf-8'))

    async def _pubsub_data_reader(self):

        pubsub = await self.pubsub.subscribe(f"worker:{self.worker_id}")
        try:
            async for message in pubsub.listen():
                if message and message['type'] == 'message':
                    data = message["data"].decode("utf-8")
                    try:
                        parsed_data = json.loads(data)
                        key = parsed_data.get('key')
                        await reader.readers[key](parsed_data)

                    except json.JSONDecodeError:
                        logger.error(f"Noto‘g‘ri xabar formati: {data}")
        except Exception as exc:
            logger.exception(f"_pubsub_data_reader funksiyasida xato: {exc}")
        finally:
            await pubsub.unsubscribe(f"worker:{self.worker_id}")

    async def send_error(self, message: str, websocket: WebSocket):
        await websocket.send_json({"status": "error", "message": message})


chat_ws_manager = ChatWebSocketManager()
