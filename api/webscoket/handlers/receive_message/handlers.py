from uuid import UUID

import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import db_helper
from models import User, Member, Message, Conversation, SecondaryFile
from resources.enums import FileType
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


async def _check_user_is_member(
        session: AsyncSession,
        user_id: int,
        conversation_uuid: UUID,
):
    return True
    query = (
        sa.select(
            sa.exists()
            .where(
                Member.user_id == user_id,
                Member.deleted.is_(False),
            )
            .join(Conversation, Conversation.id == Member.conversation_id)
            .where(
                Conversation.uuid == conversation_uuid,
            )
        )
    )
    return (await session.execute(query)).scalar()


@dp.command("send_message")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendMessageModel,
        user: User,
):
    async with db_helper.session() as session:
        checking = _check_user_is_member(session, user.id, payload.conversation_uuid)
        if checking is False:
            return await websocket.send_json(
                {'type': 'error', 'message': "You are not a member of this conversation"}
            )
        message = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=payload.conversation_id,
            reply_id=payload.reply_id,
        )
        session.add(message)
        await session.commit()

    return message.as_dict()


@dp.command("send_photo")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendPhotosModel,
        user: User,
):
    async with db_helper.session() as session:
        checking = _check_user_is_member(session, user.id, payload.conversation_uuid)
        if checking is False:
            return await websocket.send_json(
                {'type': 'error', 'message': "You are not a member of this conversation"}
            )
        msg = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=payload.conversation_id,
            reply_id=payload.reply_id,
            type=FileType.PHOTO
        )
        await session.flush()

        files = []
        for file_id in payload.files:
            files.append(SecondaryFile(
                message_id=msg.id,
                file_id=file_id,
            ))

        await session.add_all(files)

        await session.commit()

    return msg.as_dict()
