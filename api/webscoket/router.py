import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import db_helper
from models import User
from resources.managers.ws.manager import chat_ws_manager
from utils.routes import WSDispatchers
from .handlers import chats, conversation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

__ws_dispatchers__ = WSDispatchers(
    dispatchers=(
        chats.dp,
        conversation.dp,
    )
)


@router.get("/{user_id}/{tenant}")
async def user_websocket(
        ws: WebSocket,
        user_id: int,
        tenant: str,
):
    return "salom"


@router.websocket("/{user_id}/{tenant}")
async def user_websocket(
        ws: WebSocket,
        user_id: int,
        tenant: str,
):
    async with db_helper.session() as session:
        session: AsyncSession

        user, _ = await User.repo.db_get_or_create(session, tenant=tenant, user_id=user_id)
        user: User

    conn_id = user.conn_id
    await chat_ws_manager.connect(conn_id, ws)

    try:
        while True:
            message = await ws.receive_json()
            command = message.get("command")
            payload = message.get("payload")
            request_id = message.get("request_id")
            if not command:
                await chat_ws_manager.send_error(websocket=ws, message='You should provide message type')
                continue

            if ("payload" in message) and not payload:
                await chat_ws_manager.send_error(websocket=ws, message='You should provide payload')
                continue

            if not (func := chat_ws_manager.get_command_func(command)):
                logger.error(f"No Command [{command}] exists")
                await chat_ws_manager.send_error(websocket=ws, message=f"Command: {command} was not found")
                continue

            await chat_ws_manager.call_command(
                request_id=request_id,
                command=command,
                websocket=ws,
                user=user,
                payload=payload,
            )

    except WebSocketDisconnect:
        await chat_ws_manager.disconnect(conn_id)
