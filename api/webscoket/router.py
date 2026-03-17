import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from resources.managers.ws.manager import chat_ws_manager
from . import handlers  # noqa

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.websocket("/{user_id}/{tenant}")
async def user_websocket(
        ws: WebSocket,
        user_id: int,
        tenant: str,
):
    conn_id = f"{user_id}-{tenant}"
    await chat_ws_manager.connect(conn_id, ws)

    try:
        while True:
            message = await ws.receive_json()

            if not (_type := message.get('type')):
                await chat_ws_manager.send_error(websocket=ws, message='You should provide message type')
                continue

            if not (handler := chat_ws_manager.handlers.get(_type)):
                logger.error(f"No handler [{_type}] exists")
                await chat_ws_manager.send_error(f"Type: {_type} was not found", ws)
                continue

            await handler(
                websocket=ws,
                conn_id=conn_id,
                data=message["data"],

            )
    except WebSocketDisconnect:
        await chat_ws_manager.disconnect(conn_id)
