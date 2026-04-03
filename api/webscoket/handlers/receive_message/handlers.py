import typing as t
from uuid import UUID

import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import db_helper
from models import User, Member, Message, Conversation, SecondaryFile
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


async def _get_chat_id(
        session: AsyncSession,
        chat_uuid: UUID
) -> t.Tuple[t.Optional[str], t.Optional[int]]:
    conversation_id = await Conversation.get_conversation_id(session, chat_uuid)
    if not conversation_id:
        return 'Chat not found', conversation_id
    return None, conversation_id


async def _check_user_is_member(
        session: AsyncSession,
        user_id: int,
        conversation_id: int,
):
    return True
    query = (
        sa.select(
            sa.exists()
            .where(
                Member.conversation_id == conversation_id,
                Member.user_id == user_id,
                Member.deleted.is_(False),
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
        error, conversation_id = await _get_chat_id(session, payload.conversation_uuid)
        if error:
            return await websocket.send_json(
                {'type': 'error', 'message': error}
            )
        checking = await _check_user_is_member(session, user.id, conversation_id)
        if checking is False:
            return await websocket.send_json(
                {'type': 'error', 'message': "You are not a member of this conversation"}
            )
        message = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=conversation_id,
            reply_id=payload.reply_id,
        )
        session.add(message)
        await session.commit()

    return message.as_dict()


@dp.command("send_file")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendFilesModel,
        user: User,
):
    async with db_helper.session() as session:
        error, conversation_id = await _get_chat_id(session, payload.conversation_uuid)
        if error:
            return await websocket.send_json(
                {'type': 'error', 'message': error}
            )
        checking = await _check_user_is_member(session, user.id, conversation_id)
        if checking is False:
            return await websocket.send_json(
                {'type': 'error', 'message': "You are not a member of this conversation"}
            )
        msg = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=conversation_id,
            reply_id=payload.reply_id,
            type=payload.type
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
