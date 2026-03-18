import asyncio
import logging
import typing as t
from uuid import uuid4

from fastapi import WebSocket

from config.redis import cache
from config.redis.pubsub import pubsub as pubsub_redis
from resources.managers.ws.connections import connections

if t.TYPE_CHECKING:
    from .dispatcher import WSDispatcher
logger = logging.getLogger(__name__)


class ChatWebSocketManager:
    def __init__(self, pubsub=pubsub_redis):
        self.worker_id: str = str(uuid4())[-4:]
        self._handlers: dict = {}
        self.tasks = []
        self.pubsub = pubsub

    def get_handler(self, command: str) -> t.Optional[t.Callable]:
        return self._handlers.get(command)

    def include_handler(self, handler: "WSDispatcher"):
        functions = handler.get_handlers()
        self._handlers.update(functions)

    async def stop(self):
        if self.pubsub:
            await self.pubsub.disconnect()
        for task in self.tasks:
            task.cancel()

    async def send_error(self, websocket: WebSocket, message: str):
        await websocket.send_json({'type': 'error', 'message': message})

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

    async def send_broadcast(self, conn_ids: t.Iterable, data: dict, ):
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


chat_ws_manager = ChatWebSocketManager()
