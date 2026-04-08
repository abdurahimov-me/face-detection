from fastapi import WebSocket

from models import User
from resources.managers.ws.dispatcher import WSDispatcher
from resources.managers.ws.manager import chat_ws_manager
from . import schemas

dp = WSDispatcher()


@dp.command("mark_as_typing")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.MarkAsTyping
):
    data = user.as_dict()
    data["conversation_uuid"] = str(payload.conversation_uuid)
    await chat_ws_manager.send_to_conv(
        conv_id=payload.conversation_uuid,
        data=data,
        event="user_typing",
    )
    return {
        "typing": True
    }
