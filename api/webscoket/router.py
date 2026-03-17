import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from config.db import db_helper
from resources.managers.ws.manager import chat_ws_manager
from . import handlers  # noqa

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
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
    conn_id = f"{user_id}-{tenant}"
    await chat_ws_manager.connect(conn_id, ws)

    async with db_helper.session() as session:
        session: AsyncSession

    try:
        while True:
            message = await ws.receive_json()

            if not (command := message.get('command')):
                await chat_ws_manager.send_error(websocket=ws, message='You should provide message type')
                continue

            if not (data := message.get('data')):
                await chat_ws_manager.send_error(websocket=ws, message='You should provide data')
                continue

            if not (handler := chat_ws_manager.handlers.get(command)):
                logger.error(f"No handler [{command}] exists")
                await chat_ws_manager.send_error(f"Type: {command} was not found", ws)
                continue

            await handler(
                websocket=ws,
                conn_id=conn_id,
                data=data,

            )
    except WebSocketDisconnect:
        await chat_ws_manager.disconnect(conn_id)
