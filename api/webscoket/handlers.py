from resources.managers.ws.manager import chat_ws_manager as manager
from fastapi import WebSocket

@manager.handler("typing")
async def typing(websocket: WebSocket, conn_id: str , data: dict):

    pass

