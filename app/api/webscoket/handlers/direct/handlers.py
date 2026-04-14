from fastapi import WebSocket
import sqlalchemy as sa

from config import AWS_SETTINGS
from config.db import db_helper
from integrations.grpc.services import user_grpc_service
from models import Conversation, Member, Message
from models import User
from resources.enums import ConversationType
from resources.managers.ws.dispatcher import WSDispatcher
from utils.exceptions import WSException
from . import schemas
from resources.managers.ws.manager import chat_ws_manager
dp = WSDispatcher()


@dp.command("start_direct_conversation")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        payload: schemas.StartConversation,
):
    async with db_helper.session() as session:

        hr_data = await user_grpc_service.get_user(
            user_id=payload.partner.user_id,
            tenant=payload.partner.tenant
        )
        if hr_data is None:
            raise WSException("HR service is not available")

        partner, _ = await User.repo.db_get_or_create(
            session,
            user_id=payload.partner.user_id,
            tenant=payload.partner.tenant,
            defaults={
                "first_name": hr_data.first_name or "",
                "last_name": hr_data.last_name or "",
                "middle_name": hr_data.middle_name or "",
                "face": hr_data.face or "",
                "extra_data": {
                    "first_name": hr_data.first_name or "",
                    "last_name": hr_data.last_name or "",
                    "middle_name": hr_data.middle_name or "",
                    "face": hr_data.face or "",
                }
            }
        )

        existing_chat = await session.execute(
            sa.select(Conversation)
            .join(Member, Member.conversation_id == Conversation.id)
            .where(
                Conversation.type == ConversationType.DIRECT,
                Member.user_id.in_([user.id, partner.id])
            )
            .group_by(Conversation.id)
            .having(sa.func.count(Member.user_id) == 2)
            .limit(1)
        )
        existing_chat = existing_chat.scalar_one_or_none()

        if existing_chat:
            return {
                "uuid": existing_chat.uuid,
                "name": partner.full_name,
                "type": existing_chat.type,
                "owner_id": existing_chat.owner_id,
                "unread": 0,
                "members": 2,
                "online": False,
                "unread_message_id": None,
                "last_message": None,
                "created": False
            }

        chat = Conversation(
            name=" ",
            type=ConversationType.DIRECT,
            owner_id=user.id,
        )
        session.add(chat)
        await session.flush()
        session.add_all(
            [Member(user_id=user.id, conversation_id=chat.id),
             Member(user_id=partner.id, conversation_id=chat.id)]
        )
        session.add(Message.create_event_message(
            "created_direct",
            conv_id=chat.id,
            sender_id=user.id,
        ))
        await session.commit()

        data = {
            "uuid": str(chat.uuid),
            "name": partner.full_name,
            "type": chat.type,
            "owner_id": chat.owner_id,
            "unread": 1,
            "members": 2,
            "online": False,
            "unread_message_id": None,
            "last_message": None,
            "created": True,
            "poster": AWS_SETTINGS.make_hr_cdn_url(partner.face),
        }
        event_data = data.copy()
        event_data["name"] = user.full_name
        event_data["online"] = True
        event_data["poster"] = AWS_SETTINGS.make_hr_cdn_url(user.face)
        await chat_ws_manager.send_to_conn(
            partner.conn_id,
            event_data,
            "new_conversation"
        )
        return data
