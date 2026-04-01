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
        direction = payload.direction

        if cursor is None:
            first_unread = await session.scalar(
                sa.select(sa.func.min(Message.id))
                .where(
                    Message.conversation_id == payload.conversation_id,
                    Message.deleted.is_(False),
                    Message.sender_id != user.id,
                    ~sa.exists().where(
                        sa.and_(
                            MessageRead.message_id == Message.id,
                            MessageRead.user_id == user.id,
                        )
                    )
                )
            )

            cursor = first_unread

        unread_count = await session.scalar(
            sa.select(sa.func.count(Message.id))
            .where(
                Message.conversation_id == payload.conversation_id,
                Message.deleted.is_(False),
                Message.sender_id != user.id,
                ~sa.exists().where(
                    sa.and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user.id,
                    )
                )
            )
        )

        base_stmt = (
            sa.select(
                Message.id,
                Message.text,
                Message.sender_id,
                Message.created_at,
                Message.reply_id,
                Message.conversation_id,
                User.user_id,
            )
            .join(User, User.id == Message.sender_id)
            .where(
                Message.conversation_id == payload.conversation_id,
                Message.deleted.is_(False),
            )
            .limit(20)
        )

        if direction == "up":
            stmt = (
                base_stmt
                .where(Message.id < cursor)
                .order_by(Message.id.desc())
            )
            result = (await session.execute(stmt)).mappings().all()
            prev_cursor = result[-1]["id"] if len(result) == 20 else None
            next_cursor = cursor

        elif direction == "down":
            stmt = (
                base_stmt
                .where(Message.id >= cursor)
                .order_by(Message.id.asc())
            )
            result = (await session.execute(stmt)).mappings().all()
            next_cursor = result[-1]["id"] + 1 if len(result) == 20 else None
            prev_cursor = cursor

        else:
            if cursor is not None:
                up_stmt = (
                    base_stmt
                    .where(Message.id < cursor)
                    .order_by(Message.id.desc())
                    .limit(10)
                )
                down_stmt = (
                    base_stmt
                    .where(Message.id >= cursor)
                    .order_by(Message.id.asc())
                    .limit(10)
                )
                up_result = (await session.execute(up_stmt)).mappings().all()
                down_result = (await session.execute(down_stmt)).mappings().all()

                result = list(reversed(up_result)) + list(down_result)
                prev_cursor = up_result[-1]["id"] if len(up_result) == 10 else None
                next_cursor = down_result[-1]["id"] + 1 if len(down_result) == 10 else None
            else:
                stmt = base_stmt.order_by(Message.id.desc())
                result = (await session.execute(stmt)).mappings().all()
                result = list(reversed(result))
                prev_cursor = result[0]["id"] - 1 if len(result) == 20 else None
                next_cursor = None

        data = schemas.ResponseMessageModel(
            messages=result,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            unread_count=unread_count,
        ).model_dump_json()

        await websocket.send_text(data)
