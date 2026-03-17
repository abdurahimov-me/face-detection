from models import User
from resources.managers.ws.manager import chat_ws_manager
from fastapi import WebSocket

@chat_ws_manager.handler("get_chats")
async def handle_chats(
        websocket: WebSocket,
        conn_id: str,
        data: dict,
        user: User
):
    await websocket.send_json({"salom": "asdasdas"})