from fastapi import WebSocket

from config.db import db_helper
from models import User, Conversation
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
    async with db_helper.session() as session:
        conv_id = await Conversation.get_conversation_field(session, payload.conversation_uuid, "id")
    data = user.as_dict()
    data["conversation_uuid"] = str(payload.conversation_uuid)
    await chat_ws_manager.send_to_conv(
        conv_id,
        data=data,
        event="user_typing",
        exclude_conn=user.conn_id,
    )
    return {
        "typing": True
    }
