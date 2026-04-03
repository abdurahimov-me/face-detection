import typing as t

import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import User, Message, MessageRead, Conversation
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


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
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Message.deleted.is_(False),
                    Message.sender_id != user.id,
                    Conversation.uuid == payload.conversation_uuid,
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

        if direction == "up" and cursor:
            stmt = (
                base_stmt
                .where(Message.id < cursor)
                .order_by(Message.id.desc())
            )
            result = (await session.execute(stmt)).mappings().all()
            prev_cursor = result[-1]["id"] if len(result) == 20 else None
            next_cursor = cursor

        elif direction == "down" and cursor:
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
    return schemas.ResponseMessageModel(
        prev_cursor=prev_cursor,
        next_cursor=next_cursor,
        unread_count=unread_count,
        messages=result,
    )


@dp.command("mark_as_read")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.MarkAsReadModel,
        user: User,
        request_id: t.Any = None,
):
    async with db_helper.session() as session:
        conversation_id = await session.scalar(
            sa.select(Conversation.id)
            .where(Conversation.uuid == payload.conversation_uuid)
        )

        if not conversation_id:
            return {
                "marked": 0
            }

        unread_ids = (await session.execute(
            sa.select(Message.id)
            .where(
                Message.conversation_id == conversation_id,
                Message.id <= payload.message_id,
                Message.sender_id != user.id,
                Message.deleted.is_(False),
                ~sa.exists().where(
                    sa.and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user.id,
                    )
                )
            )
        )).scalars().all()

        if not unread_ids:
            return

        await session.execute(
            sa.insert(MessageRead).values([
                {"message_id": msg_id, "user_id": user.id}
                for msg_id in unread_ids
            ])
        )
        await session.commit()
        return {
            "marked": len(unread_ids)
        }
