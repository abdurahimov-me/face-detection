import asyncio
import inspect
import logging
import typing as t
from uuid import uuid4

from fastapi import WebSocket
from fastapi import params as fastapi_params
from pydantic import ValidationError, BaseModel

from config.redis import cache
from config.redis.pubsub import pubsub as pubsub_redis
from resources.managers.ws.connections import connections
from utils.exceptions import WSException
from .schemas import BaseWSResponse

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from .dispatcher import WSDispatcher


class ChatWebSocketManager:
    def __init__(self, pubsub=pubsub_redis):
        self.worker_id: str = str(uuid4())[-4:]
        self._commands: dict = {}
        self.tasks = []
        self.pubsub = pubsub

    async def _resolve_depends(self, depends: fastapi_params.Depends):
        dep_func = depends.dependency
        dep_sig = inspect.signature(dep_func)
        dep_kwargs = {}

        for name, param in dep_sig.parameters.items():
            if isinstance(param.default, fastapi_params.Depends):
                dep_kwargs[name] = await self._resolve_depends(param.default)

        if inspect.isasyncgenfunction(dep_func):
            gen = dep_func(**dep_kwargs)
            return await gen.__anext__()

        if inspect.iscoroutinefunction(dep_func):
            return await dep_func(**dep_kwargs)

        return dep_func(**dep_kwargs)

    async def call_command(
            self,
            command: str,
            websocket: WebSocket,
            **context
    ):
        func = self._commands.get(command)
        if not func:
            return None

        sig = inspect.signature(func)
        kwargs = {}

        for name, param in sig.parameters.items():
            if name in context:
                if name == "payload":
                    annotation = param.annotation
                    if (
                            annotation is not inspect.Parameter.empty
                            and isinstance(annotation, type)
                            and issubclass(annotation, BaseModel)
                    ):
                        raw = context[name]
                        try:
                            kwargs[name] = annotation.model_validate(raw)
                        except ValidationError as e:
                            return await self.send_error(websocket=websocket, message=str(e))
                        continue

                kwargs[name] = context[name]

            elif isinstance(param.default, fastapi_params.Depends):
                kwargs[name] = await self._resolve_depends(param.default)
        try:
            data = await func(websocket, **kwargs)
            res = BaseWSResponse(
                success=True,
                request_id=context.get("request_id"),
                command=command,
                data=data,
            )
            return await websocket.send_text(res.model_dump_json())
        except WSException as e:
            return await websocket.send_json({
                "success": False,
                "type": "error",
                "message": e.message,
            })
        except Exception as e:
            return await websocket.send_json({
                "success": False,
                "type": "critical_error",
                "message": str(e),
            })

    def get_command_func(self, command: str) -> t.Optional[t.Callable]:
        return self._commands.get(command)

    def include_handler(self, handler: "WSDispatcher"):
        functions = handler.get_handlers()
        self._commands.update(functions)

    async def stop(self):
        if self.pubsub:
            await self.pubsub.disconnect()
        for task in self.tasks:
            task.cancel()

    async def send_error(self, websocket: WebSocket, message: str):
        await websocket.send_json(
            {
                'success': False,
                'type': 'error',
                'message': message
            }
        )

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
        conn_id = str(conn_id)
        if websocket := connections.get(conn_id):
            await websocket.send_json(data)
        else:
            worker_id = await cache.client.hget("user_connections", conn_id)
            data = dict(data=data, conn_id=conn_id, key='conn_id')
            if worker_id:
                await self.publish_to_worker(data=data, worker_id=worker_id.decode('utf-8'))


chat_ws_manager = ChatWebSocketManager()
