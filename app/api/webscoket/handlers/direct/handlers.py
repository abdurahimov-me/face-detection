from fastapi import WebSocket

from config.db import db_helper
from integrations.grpc.services import user_grpc_service
from models import Conversation, Member
from models import User
from resources.enums import ConversationType
from resources.managers.ws.dispatcher import WSDispatcher
from utils.exceptions import WSException
from . import schemas

dp = WSDispatcher()


@dp.command("start_direct_conversation")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.StartConversation,
):
    async with db_helper.session() as session:
        partner_user_id, partner_tenant = payload.partner.split(":")

        hr_data = await user_grpc_service.get_user(user_id=int(partner_user_id), tenant=partner_tenant)
        if hr_data is None:
            raise WSException("HR service is not available")

        partner, _ = await User.repo.db_get_or_create(
            session,
            user_id=int(partner_user_id),
            tenant_id=partner_tenant,
            defaults={
                "first_name": hr_data.first_name,
                "last_name": hr_data.last_name,
                "middle_name": hr_data.middle_name,
                "face": hr_data.face,
                "extra_data": {
                    "first_name": hr_data.first_name,
                    "last_name": hr_data.last_name,
                    "middle_name": hr_data.middle_name,
                    "face": hr_data.face,
                }
            }
        )
        partner: User
        chat = Conversation(
            name=" ",
            type=ConversationType.DIRECT,
            owner_id=user.id,
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
            "type": chat.type,
            "owner_id": chat.owner_id,
            "unread": 0,
            "members": 2,
            "online": False,
            "unread_message_id": None,
            "last_message": None,
        }
