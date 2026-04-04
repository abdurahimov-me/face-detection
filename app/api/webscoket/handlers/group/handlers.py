from fastapi import WebSocket

from config.db import db_helper
from models import Conversation, Member
from models import User
from resources.enums import ConversationType
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


@dp.command("create_group")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.StartConversation,
):
    async with db_helper.session() as session:
        partner_user_id, partner_tenant = payload.partner.split(":")
        partner, _ = await User.repo.db_get_or_create(session, user_id=int(partner_user_id), tenant_id=partner_tenant)
        partner: User
        chat = Conversation(
            name=" ",
            type=ConversationType.DIRECT,
        )
        session.add(chat)
        await session.flush()
        session.add_all(
            [Member(user_id=user.id, conversation_id=chat.id), Member(user_id=partner.id, conversation_id=chat.id)]
        )
        await session.commit()
        return {
            "uuid": chat.uuid,
            "name": chat.name,
        }
