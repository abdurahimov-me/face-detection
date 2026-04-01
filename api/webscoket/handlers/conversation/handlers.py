import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import User, Member, Message
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


@dp.command("send_message")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendMessageModel,
        user: User,
):
    async with db_helper.session() as session:
        query = sa.select(sa.exists().where(
            Member.user_id == user.id,
            Member.conversation_id == payload.conversation_id,
            Member.deleted.is_(False),
        ))
        checking = await session.execute(query)
        if checking is False:
            pass

        session.add(Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=payload.conversation_id,
            reply_id=payload.reply_id,
        ))
        await session.commit()
    await websocket.send_json({"success": True, "message": "Message sent"})
