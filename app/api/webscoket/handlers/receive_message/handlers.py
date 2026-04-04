from uuid import UUID

import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import db_helper
from models import User, Member, Message, Conversation, SecondaryFile
from resources.managers.ws.dispatcher import WSDispatcher
from resources.managers.ws.manager import chat_ws_manager
from utils.exceptions import WSException
from . import schemas

dp = WSDispatcher()


async def _get_chat_id(
        session: AsyncSession,
        chat_uuid: UUID
) -> int:
    conversation_id = await Conversation.get_conversation_field(session, chat_uuid, "uuid")
    if not conversation_id:
        raise WSException(f"No conversation with uuid: {chat_uuid}")
    return conversation_id


async def _check_user_is_member(
        session: AsyncSession,
        user_id: int,
        conversation_id: int,
):
    member_exists = sa.exists().where(
        Member.conversation_id == conversation_id,
        Member.user_id == user_id,
        Member.deleted.is_(False),
    )

    owner_exists = sa.exists().where(
        Conversation.id == conversation_id,
        Conversation.owner_id == user_id,
        Conversation.deleted.is_(False),
    )

    query = sa.select(
        sa.or_(member_exists, owner_exists)
    )

    checking = (await session.execute(query)).scalar()

    if not checking:
        raise WSException("User is not member or owner of conversation")


@dp.command("send_message")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendMessageModel,
        user: User,
):
    async with db_helper.session() as session:
        conversation_id = await _get_chat_id(session, payload.conversation_uuid)
        await _check_user_is_member(session, user.id, conversation_id)
        message = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=conversation_id,
            reply_id=payload.reply_id,
        )
        session.add(message)
        await session.commit()
    await chat_ws_manager.send_to_conv(
        conversation_id,
        message.as_dict(),
        "new_message",
        user.conn_id
    )
    return message.as_dict()


@dp.command("send_file")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendFilesModel,
        user: User,
):
    async with db_helper.session() as session:
        conversation_id = await _get_chat_id(session, payload.conversation_uuid)
        await _check_user_is_member(session, user.id, conversation_id)
        msg = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=conversation_id,
            reply_id=payload.reply_id,
            type=payload.type
        )
        session.add(msg)
        await session.flush()

        files = []
        for file_id in payload.files:
            files.append(SecondaryFile(
                message_id=msg.id,
                file_id=file_id,
            ))

        session.add_all(files)

        await session.commit()
    await chat_ws_manager.send_to_conv(
        conversation_id,
        msg.as_dict(),
        "new_message",
        user.conn_id
    )
    return msg.as_dict()
