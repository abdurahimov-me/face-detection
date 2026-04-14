import typing as t

import sqlalchemy as sa
from fastapi import WebSocket

from config import AWS_SETTINGS
from config.db import db_helper
from config.redis import cache
from models import Conversation, Message, MessageRead, Member, File
from models import User
from resources.enums import ConversationType
from resources.managers.ws.connections import connections_manager
from resources.managers.ws.dispatcher import WSDispatcher

dp = WSDispatcher()


@dp.command("get_chats")
async def handle_chats(
        websocket: WebSocket,
        user: User,
):
    async with db_helper.session() as session:

        conv_full_stmt = (
            sa.select(
                Conversation.id,
                Conversation.uuid,
                Conversation.name,
                Conversation.type,
                Conversation.created_at,
                File.file.label("poster"),
            )
            .select_from(Conversation)
            .join(Member, Member.conversation_id == Conversation.id)
            .join(File, File.id == Conversation.poster_id, isouter=True)
            .where(Member.deleted.is_(False), Member.user_id == user.id)
            .order_by(Conversation.id.desc())
        )
        conversations = list((await session.execute(conv_full_stmt)).mappings().all())
        direct_chats = [c.id for c in conversations if c.type == ConversationType.DIRECT]
        partners_stmt = (
            sa.select(User, Conversation.id)
            .select_from(User)
            .join(Member, Member.user_id == User.id)
            .join(Conversation, Conversation.id == Member.conversation_id)
            .where(Conversation.id.in_(direct_chats), Member.deleted.is_(False), User.id != user.id)
        )
        partners = (await session.execute(partners_stmt)).fetchall()
        partners_map = {i[1]: i[0] for i in partners}

        conv_ids = [c.id for c in conversations]

        if not conv_ids:
            return []

        last_msg_subq = (
            sa.select(
                Message.id,
                Message.text,
                Message.sender_id,
                Message.created_at,
                Message.topic_id,
                Message.reply_id,
                Message.conversation_id,
                Message.type,
                User.first_name,
                User.last_name,
                User.user_id,
                sa.func.row_number().over(
                    partition_by=Message.conversation_id,
                    order_by=Message.id.desc()
                ).label("rn")
            )
            .join(User, User.id == Message.sender_id)
            .where(
                Message.conversation_id.in_(conv_ids),
                Message.deleted.is_(False),
            )
            .subquery()
        )

        last_messages_stmt = sa.select(last_msg_subq).where(last_msg_subq.c.rn == 1)
        last_messages_res = (await session.execute(last_messages_stmt)).mappings().all()
        last_messages = {m["conversation_id"]: dict(m) for m in last_messages_res}

        # Unread count
        unread_stmt = (
            sa.select(
                Message.conversation_id,
                sa.func.count(Message.id).label("unread")
            )
            .where(
                Message.conversation_id.in_(conv_ids),
                Message.deleted.is_(False),
                Message.sender_id != user.id,
                ~sa.exists().where(
                    sa.and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user.id,
                    )
                )
            )
            .group_by(Message.conversation_id)
        )
        unread_res = (await session.execute(unread_stmt)).mappings().all()
        unread_map = {r["conversation_id"]: r["unread"] for r in unread_res}

        members_stmt = (
            sa.select(
                Member.conversation_id,
                sa.func.count(Member.id).label("members")
            )
            .where(
                Member.conversation_id.in_(conv_ids),
                Member.deleted.is_(False),
            )
            .group_by(Member.conversation_id)
        )
        members_res = (await session.execute(members_stmt)).mappings().all()
        members_map = {r["conversation_id"]: r["members"] for r in members_res}

        first_unread_stmt = (
            sa.select(
                Message.conversation_id,
                sa.func.min(Message.id).label("unread_message_id")
            )
            .where(
                Message.conversation_id.in_(conv_ids),
                Message.deleted.is_(False),
                Message.sender_id != user.id,
                ~sa.exists().where(
                    sa.and_(
                        MessageRead.message_id == Message.id,
                        MessageRead.user_id == user.id,
                    )
                )
            )
            .group_by(Message.conversation_id)
        )
        first_unread_res = (await session.execute(first_unread_stmt)).mappings().all()
    first_unread_map = {r["conversation_id"]: r["unread_message_id"] for r in first_unread_res}

    result = []
    for conv in conversations:
        item = dict(conv)
        conv_id = conv["id"]
        last_message: t.Optional[t.Dict] = last_messages.get(conv_id)
        if last_message:
            last_message["read"] = True
        if conv["type"] == ConversationType.DIRECT:
            if partner := partners_map.get(conv_id):
                partner: User
                connections_manager.join_channel(user.conn_id, str(conv_id))
                item["poster"] = AWS_SETTINGS.make_hr_cdn_url(partner.face)
                item["name"] = partner.full_name
                item["encrypt"] = partner.encrypt
                item["online"] = await cache.get(f"user_online:{partner.id}")
            else:
                continue
        else:
            connections_manager.join_channel(user.conn_id, str(conv_id))
            item["poster"] = AWS_SETTINGS.make_cdn_url(conv["poster"])
        item.update({
            "unread": unread_map.get(conv_id, 0),
            "members": members_map.get(conv_id, 0),
            "unread_message_id": first_unread_map.get(conv_id),
            "last_message": last_message,
        })
        result.append(item)

    result.sort(
        key=lambda x: (
            x["last_message"].get("created_at")
            if x["last_message"]
            else x.get("created_at")
        ),
        reverse=True
    )

    return result
