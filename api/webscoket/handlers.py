from resources.managers.ws.manager import chat_ws_manager as manager
from fastapi import WebSocket

@manager.handler("typing")
async def typing(con: WebSocket, data):

    pass

