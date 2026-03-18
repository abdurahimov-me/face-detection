from fastapi import WebSocket

from models import User
from resources.managers.ws.dispatcher import WSDispatcher

dispatcher = WSDispatcher()


@dispatcher.handler("get_chats")
async def handle_chats(
        websocket: WebSocket,
        conn_id: str,
        payload: dict,
        user: User
):
    await websocket.send_json({"salom": "asdasdas"})
