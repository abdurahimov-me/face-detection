from fastapi import WebSocket

from resources.managers.ws.manager import chat_ws_manager as manager


@manager.handler("typing")
async def typing(websocket: WebSocket, conn_id: str, data: dict):
    pass



@manager.handler("send_message")
async def typing(websocket: WebSocket, conn_id: str, data: dict):
    pass