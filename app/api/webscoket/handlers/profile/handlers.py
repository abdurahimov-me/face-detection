from fastapi import WebSocket

from models import User
from resources.managers.ws.dispatcher import WSDispatcher

dp = WSDispatcher()


@dp.command("mark_as_typing")
async def handle_chats(
        websocket: WebSocket,
        user: User,
):
    await user.mark_as_typing()
    return {
        "typing": True
    }
