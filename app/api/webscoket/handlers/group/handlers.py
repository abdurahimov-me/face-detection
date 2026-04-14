import typing as t

import sqlalchemy as sa
from fastapi import WebSocket
from sqlalchemy.dialects.postgresql import insert as psql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from config import AWS_SETTINGS
from config.db import db_helper
from integrations.grpc.services import user_grpc_service
from models import Conversation, Member, File, Message
from models import User
from resources.enums import ConversationType, MemberType
from resources.managers.ws.dispatcher import WSDispatcher
from resources.managers.ws.manager import chat_ws_manager
from utils import utcnow
from utils.customs.formats.fernet import UserEncrypt
from utils.exceptions import WSException
from . import schemas

dp = WSDispatcher()


async def _get_or_crate_users_from_encrypt(
        session: AsyncSession,
        users_encrypt: list[UserEncrypt],
        main_tenant: str
):
    pairs = []
    user_ids = []
    for user_fernet in users_encrypt:
        pairs.append(user_fernet.get_both())
        user_ids.append(user_fernet.user_id)
    hr_users_data = await user_grpc_service.get_users(user_ids=user_ids, tenant=main_tenant)
    if hr_users_data is None:
        raise WSException("HR service is not available")

    hr_users_data = {(d.id, main_tenant): d for d in hr_users_data}

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
        hr_data = hr_users_data.get((user_id, tenant))
        if hr_data and (user_id, tenant) not in existing_map:
            to_create.append(
                User(
                    user_id=user_id,
                    tenant=tenant,
                    first_name=hr_data.first_name,
                    last_name=hr_data.last_name,
                    middle_name=hr_data.middle_name,
                    face=hr_data.face,
                    extra_data={
                        "first_name": hr_data.first_name,
                        "last_name": hr_data.last_name,
                        "middle_name": hr_data.middle_name,
                        "face": hr_data.face,
                    }

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
        all_users: t.List[User] = await _get_or_crate_users_from_encrypt(
            session,
            payload.users,
            main_tenant=user.tenant
        )

        chat = Conversation(
            name=payload.name,
            type=ConversationType.GROUP,
            owner_id=user.id,
            poster_id=payload.poster_id,
        )
        session.add(chat)
        await session.flush()
        members = [
            {
                "user_id": u.id,
                "conversation_id": int(chat.id),
                "role": MemberType.MEMBER,
                "joined_at": utcnow()
            }
            for u in all_users
        ]
        stmt = psql_insert(Member).values(members).on_conflict_do_nothing()
        await session.execute(stmt)
        session.add(Member(user_id=user.id, conversation_id=chat.id, role=MemberType.OWNER))
        session.add(Message.create_event_message("created_group", conv_id=chat.id, sender_id=user.id))
        await session.commit()

        data = {
            "uuid": str(chat.uuid),
            "name": chat.name,
            "type": chat.type,
            "owner_id": chat.owner_id,
            "unread": 1,
            "members": len(all_users) + 1,
            "online": False,
            "unread_message_id": None,
            "last_message": None,
            "created": True,
        }
        for u in all_users:
            await chat_ws_manager.send_to_conn(
                conn_id=u.conn_id,
                data=data,
                event="new_conversation"
            )
        return data


@dp.command("get_users_from_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.GetUsersFromGroup,
):
    async with db_helper.session() as session:
        conversation_id = await Conversation.get_conversation_field(session, payload.conversation_uuid, "id")

        members_stmt = await session.execute(
            sa.select(
                User.id,
                User.user_id,
                User.tenant,
                User.first_name,
                User.last_name,
                Member.role,
                User.face,
                Member.joined_at,
            )
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
        users = await _get_or_crate_users_from_encrypt(session, payload.users, main_tenant=user.tenant)

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


@dp.command("edit_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.EditGroup,
):
    async with db_helper.session() as session:
        conversation_id = await Conversation.get_conversation_field(session, payload.conversation_uuid, "id")
        users = await _get_or_crate_users_from_encrypt(session, payload.users, main_tenant=user.tenant)
        await session.flush()
        conversation = await Conversation.repo.db_first(session, id=conversation_id)
        poster = None
        if payload.poster_id is not None:
            poster = await File.repo.db_first(session, id=payload.poster_id)
            if poster is None:
                raise WSException("Poster not found")

        if conversation is None:
            raise WSException("Conversation not found")
        data = payload.model_dump(exclude_unset=True)
        data.pop("conversation_uuid", None)
        for k, v in data.items():
            setattr(conversation, k, v)

        members = [
            {
                "user_id": u.id,
                "conversation_id": int(conversation_id),
                "role": MemberType.MEMBER,
                "joined_at": utcnow()
            }
            for u in users
        ]
        if members:
            stmt = psql_insert(Member).values(members).on_conflict_do_nothing()
            await session.execute(stmt)
        await session.commit()
        data = {
            "uuid": str(conversation.uuid),
            "name": conversation.name,
            "poster": AWS_SETTINGS.make_cdn_url(poster.file) if poster else None,
        }

        await chat_ws_manager.send_to_conv(
            conversation_id,
            data,
            "edit_group",
            exclude_conn=user.conn_id,
        )

        return data
