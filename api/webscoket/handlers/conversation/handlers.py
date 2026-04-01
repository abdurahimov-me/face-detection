import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import User, Member, Message, MessageRead
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


@dp.command("get_messages")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.GetMessagesModel,
        user: User,
):
    async with db_helper.session() as session:
        cursor = payload.cursor

        if cursor is None:
            last_read = await session.execute(
                sa.select(MessageRead.message_id)
                .where(MessageRead.user_id == user.id)
                .order_by(MessageRead.message_id.desc())
                .limit(1)
            )
            last_read_id = last_read.scalar_one_or_none()
            cursor = last_read_id

        stmt = (
            sa.select(
                Message.id,
                Message.text,
                Message.sender_id,
                Message.created_at,
                Message.reply_id,
                Message.conversation_id,
            )
            .where(
                Message.conversation_id == payload.conversation_id,
                Message.deleted.is_(False),
            )
            .order_by(Message.id.desc())
            .limit(20)
        )

        if cursor is not None:
            stmt = stmt.where(Message.id <= cursor)

        result = await session.execute(stmt)
        messages = result.mappings().all()

        await websocket.send_json({
            "messages": [dict(m) for m in messages],
            "next_cursor": messages[-1]["id"] - 1 if len(messages) == 20 else None,
        })
