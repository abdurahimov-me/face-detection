import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import Conversation, Message, MessageRead, Member
from models import User
from resources.managers.ws.connections import connections_manager
from resources.managers.ws.dispatcher import WSDispatcher

dp = WSDispatcher()


@dp.command("get_chats")
async def handle_chats(
        websocket: WebSocket,
        user: User,
):
    async with db_helper.session() as session:

        conv_stmt = (
            sa.select(Member.conversation_id)
            .where(Member.deleted.is_(False), Member.user_id == user.id)
        )
        conv_ids = (await session.execute(conv_stmt)).scalars().all()

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
                sa.func.row_number().over(
                    partition_by=Message.conversation_id,
                    order_by=Message.id.desc()
                ).label("rn")
            )
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

        conv_full_stmt = (
            sa.select(
                Conversation.id,
                Conversation.uuid,
                Conversation.name,
                Conversation.type,
            )
            .where(Conversation.id.in_(conv_ids))
            .order_by(Conversation.id.desc())
        )
        conversations = (await session.execute(conv_full_stmt)).mappings().all()

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
        conv_id = conv["id"]
        connections_manager.join_channel(user.conn_id, str(conv_id))
        result.append({
            **dict(conv),
            "unread": unread_map.get(conv_id, 0),
            "members": members_map.get(conv_id, 0),
            "online": False,
            "unread_message_id": first_unread_map.get(conv_id),
            "last_message": last_messages.get(conv_id),
        })

    return result
