import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from resources.managers.ws.manager import chat_ws_manager as manager
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
    await manager.connect(str(user_id), ws)

    try:
        while True:
            message = await ws.receive_json()

            if not (_type := message.get('type')):
                await manager.send_error(websocket=ws, message='You should provide message type')
                continue

            if not (handler := manager.handlers.get(_type)):
                logger.error(f"No handler [{_type}] exists")
                await manager.send_error(f"Type: {_type} was not found", ws)
                continue
            message['sender_id'] = user_id

            await handler(
                websocket=ws,
                data=message,
            )

    except WebSocketDisconnect:
        await manager.disconnect(str(user_id))
