import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy.dialects.postgresql import insert as psql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import db_helper
from models import Conversation, Member
from models import User
from resources.enums import ConversationType, MemberType
from resources.managers.ws.dispatcher import WSDispatcher
from utils import utcnow
from . import schemas

dp = WSDispatcher()


async def _get_or_crate_users_from_encrypt(
        session: AsyncSession,
        users_encrypt: list[str],
):
    pairs = []
    for user_fernet in users_encrypt:
        user_id, tenant = user_fernet.split(":")
        pairs.append((int(user_id), tenant))
    users = await session.execute(
        sa.select(User).where(
            sa.tuple_(User.user_id, User.tenant).in_(pairs)
        )
    )
    users = list(users.scalars().all())
    existing_map = {
        (u.user_id, u.tenant): u
        for u in users
    }

    to_create = []
    for user_id, tenant in pairs:
        if (user_id, tenant) not in existing_map:
            to_create.append(
                User(
                    user_id=user_id,
                    tenant=tenant,
                )
            )

    session.add_all(to_create)
    await session.flush()
    return users + to_create


@dp.command("create_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.CreateGroup,
):
    async with db_helper.session() as session:
        all_users = await _get_or_crate_users_from_encrypt(session, payload.users)

        chat = Conversation(
            name=payload.name,
            type=ConversationType.GROUP,
            owner_id=user.id,
            poster_id=payload.poster_id,
        )
        session.add(chat)
        await session.flush()
        members = []
        for u in all_users:
            members.append(Member(user_id=u.id, conversation_id=chat.id))
        members.append(Member(user_id=user.id, conversation_id=chat.id, role=MemberType.OWNER))
        session.add_all(members)
        await session.commit()

        return {
            "uuid": chat.uuid,
            "name": chat.name,
            "type": chat.type,
            "owner_id": chat.owner_id,
            "unread": 0,
            "members": len(all_users) + 1,
            "online": False,
            "unread_message_id": None,
            "last_message": None,
        }


@dp.command("get_users_from_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.GetUsersFromGroup,
):
    async with db_helper.session() as session:
        conversation_id = await Conversation.get_conversation_field(session, payload.conversation_uuid, "id")

        members_stmt = await session.execute(
            sa.select(User.id, User.first_name, User.last_name, Member.role, User.face, Member.joined_at)
            .join(Member, Member.user_id == User.id)
            .where(
                Member.conversation_id == int(conversation_id),
                User.deleted.is_(False),
                Member.deleted.is_(False),
            )
        )
        members = members_stmt.mappings().all()
        return schemas.GetUsersFromGroupResponse(
            members=members,
        )


@dp.command("add_users_to_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.AddUsersToGroup,
):
    async with db_helper.session() as session:
        conversation_id = await Conversation.get_conversation_field(session, payload.conversation_uuid, "id")
        users = await _get_or_crate_users_from_encrypt(session, payload.users)

        members = [
            {
                "user_id": u.id,
                "conversation_id": int(conversation_id),
                "role": MemberType.MEMBER,
                "joined_at": utcnow()
            }
            for u in users
        ]

        stmt = psql_insert(Member).values(members).on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()

        return {
            "members": len(users),
        }
