import asyncio
import inspect
import json
import logging
import typing as t

from fastapi import WebSocket
from fastapi import params as fastapi_params
from pydantic import ValidationError, BaseModel

from config.redis.pubsub import pubsub as pubsub_redis
from utils.exceptions import WSException
from . import types
from .connections import ConnectionManager, connections_manager
from .schemas import BaseWSResponse

logger = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from .dispatcher import WSDispatcher


class ChatWebSocketManager:
    def __init__(
            self,
            pubsub=pubsub_redis,
            connections: ConnectionManager = connections_manager,
    ):
        self._commands: dict = {}
        self.tasks: list = []
        self.pubsub = pubsub
        self.connections = connections

    async def start(self):
        await self.pubsub.connect()
        await self.pubsub.pubsub.psubscribe("conv:*", "conn:*")
        task = asyncio.create_task(self._listener())
        self.tasks.append(task)
        logger.info("ChatWebSocketManager started, listening conv:*")

    async def stop(self):
        if self.pubsub:
            await self.pubsub.disconnect()
        for task in self.tasks:
            task.cancel()

    async def _listener(self):
        async for raw in self.pubsub.pubsub.listen():
            if not isinstance(raw, dict) or raw.get("type") != "pmessage":
                continue
            try:
                message = json.loads(raw["data"])
                channel = raw.get("channel", "")

                if channel.startswith("conv:"):
                    await self._handle_conv_message(message)
                elif channel.startswith("conn:"):
                    await self._handle_conn_message(message)

            except Exception as e:
                logger.error(f"Listener error: {e}")

    async def _handle_conv_message(self, message: dict):
        conv_id = message.get("conv_id")
        data = message.get("data")
        exclude_conn = message.get("exclude_conn")
        if not conv_id or not data:
            return
        for conn_id in self.connections.channels.get(conv_id, set()):
            if conn_id == exclude_conn:
                continue
            await self.connections.send(conn_id, data)

    async def _handle_conn_message(self, message: dict):
        conn_id = message.get("conn_id")
        data = message.get("data")
        if not conn_id or not data:
            return
        await self.connections.send(conn_id, data)

    async def connect(self, conn_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections.connections[conn_id] = websocket

    async def disconnect(self, conn_id: str):
        self.connections.disconnect(conn_id)

    def join_channel(self, conn_id: str, conv_id: str):
        self.connections.join_channel(conn_id, conv_id)

    def leave_channel(self, conn_id: str, conv_id: str):
        self.connections.leave_channel(conn_id, conv_id)

    async def send_to_conv(
            self,
            conv_id,
            data: dict,
            event: types.EVENTS,
            exclude_conn: str = None,
    ):
        await self.pubsub.publish(
            f"conv:{conv_id}",
            {
                "conv_id": str(conv_id),
                "data": {
                    "event": event,
                    "data": data,
                },
                "exclude_conn": exclude_conn,
            },
        )

    async def send_to_conn(self, conn_id: str, data: dict, event: types.EVENTS):
        await self.pubsub.publish(
            f"conn:{conn_id}",
            {
                "conn_id": conn_id,
                "data": {
                    "event": event,
                    "data": data,
                },
            },
        )

    async def send_msg(self, conn_id: str, data: dict):
        await self.connections.send(str(conn_id), data)

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

    async def call_command(self, command: str, websocket: WebSocket, **context):
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
                        try:
                            kwargs[name] = annotation.model_validate(context[name])
                        except ValidationError as e:
                            return await self.send_error(websocket, str(e))
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
            return await websocket.send_json({"success": False, "type": "error", "message": e.message})
        # except Exception as e:
        #     return await websocket.send_json({"success": False, "type": "critical_error", "message": str(e)})

    def get_command_func(self, command: str) -> t.Optional[t.Callable]:
        return self._commands.get(command)

    def include_handler(self, handler: "WSDispatcher"):
        self._commands.update(handler.get_handlers())

    @staticmethod
    async def send_error(websocket: WebSocket, message: str):
        await websocket.send_json({"success": False, "type": "error", "message": message})


chat_ws_manager: ChatWebSocketManager = ChatWebSocketManager()
