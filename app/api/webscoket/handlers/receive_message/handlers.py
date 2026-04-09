import typing as t
from uuid import UUID

import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from config import AWS_SETTINGS
from config.db import db_helper
from models import User, Member, Message, Conversation, SecondaryFile, File
from resources.managers.ws.dispatcher import WSDispatcher
from resources.managers.ws.manager import chat_ws_manager
from utils.exceptions import WSException
from . import schemas

dp = WSDispatcher()


async def _get_chat_id(
        session: AsyncSession,
        chat_uuid: UUID
) -> int:
    conversation_id = await Conversation.get_conversation_field(session, chat_uuid, "id")
    if not conversation_id:
        raise WSException(f"No conversation with uuid: {chat_uuid}")
    return int(conversation_id)


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


async def _get_reply_message(
        session: AsyncSession,
        reply_id: t.Optional[int],
):
    if reply_id:
        reply_message_stmt = (
            sa.select(
                Message.id,
                Message.type,
                sa.func.left(Message.text, 20).label("reply_text"),
                User.first_name.label("reply_user_first_name"),
                User.last_name.label("reply_user_last_name"),
            )
            .select_from(Message)
            .join(User, User.id == Message.sender_id)
            .where(Message.id == reply_id)
            .limit(1)
        )
        reply_message = (await session.execute(reply_message_stmt)).mappings().first()
        if not reply_message:
            raise WSException("Reply message not found")
        return reply_message
    return None


def _get_event_data(
        message: Message,
        user: User,
        reply_message,
        conversation_uuid,
):
    event_data = message.as_dict({
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "face": AWS_SETTINGS.make_hr_cdn_url(user.face),
    })
    if reply_message:
        event_data.update({
            "reply_text": reply_message["reply_text"],
            "reply_last_name": reply_message["reply_user_last_name"],
            "reply_first_name": reply_message["reply_user_first_name"],
            "reply_type": reply_message["type"]
        })
    event_data["conversation_uuid"] = str(conversation_uuid)
    return event_data


@dp.command("send_message")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendMessageModel,
        user: User,
):
    async with db_helper.session() as session:
        conversation_id = await _get_chat_id(session, payload.conversation_uuid)
        await _check_user_is_member(session, user.id, conversation_id)
        reply_message = await _get_reply_message(session, payload.reply_id)
        message = Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=conversation_id,
            reply_id=payload.reply_id,
        )
        session.add(message)
        await session.commit()

    event_data = _get_event_data(message, user, reply_message, payload.conversation_uuid)
    await chat_ws_manager.send_to_conv(
        conversation_id,
        event_data,
        "new_message",
        user.conn_id
    )
    return event_data


@dp.command("send_file")
async def handle_chats(
        websocket: WebSocket,
        payload: schemas.SendFilesModel,
        user: User,
):
    async with db_helper.session() as session:
        conversation_id = await _get_chat_id(session, payload.conversation_uuid)
        await _check_user_is_member(session, user.id, conversation_id)

        files = await File.repo.db_filter(session, id__in=payload.files)
        if len(files) != len(payload.files):
            raise WSException("Some files not found")

        reply_message = await _get_reply_message(session, payload.reply_id)
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
    event_data = _get_event_data(msg, user, reply_message, payload.conversation_uuid)
    event_data["files"] = [{
        "id": f.id,
        "file": AWS_SETTINGS.make_cdn_url(f.file),
        "filename": f.filename,
        "size": f.size,
        "type": f.type,
        "meta_data": f.meta_data,
    } for f in files]

    await chat_ws_manager.send_to_conv(
        conversation_id,
        event_data,
        "new_message",
        user.conn_id
    )
    return event_data
