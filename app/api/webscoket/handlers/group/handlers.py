import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import Conversation, Member
from models import User
from resources.enums import ConversationType, MemberType
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


@dp.command("create_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.CreateGroup,
):
    async with db_helper.session() as session:
        pairs = []
        for user_fernet in payload.users:
            user_id, tenant = user_fernet.split(":")
            pairs.append((int(user_id), tenant))
        users = await session.execute(
            sa.select(User).where(
                sa.tuple_(User.user_id, User.tenant).in_(pairs)
            )
        )
        users = users.scalars().all()
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
        all_users = users + to_create

        chat = Conversation(
            name=payload.name,
            type=ConversationType.GROUP,
            owner_id=user.id,
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
        }
