import sqlalchemy as sa
from fastapi import WebSocket

from models import User, Conversation, Member, Message
from resources.services import BaseWSService
from . import schemas


class ChatsService(BaseWSService):

    async def get_chats(
            self,
            ws: WebSocket,
            user: User,
    ):
        stmt = (
            sa.select(
                Conversation,
            )
            # .join(Member, Member.conversation_id == Conversation.id, isouter=True)
            # .where(
            #     Member.user_id == user.id,
            #     Member.left_at.is_(None)
            # )
        )
        res = (await self.execute(stmt)).scalars().all()
        data = schemas.ConversationModelResponse(data=res).model_dump_json()
        await ws.send_text(data)

    async def send_message(
            self,
            ws: WebSocket,
            user: User,
            payload: schemas.SendMessageModel
    ):
        checking = await Member.repo.db_exists(
            self.db,
            user_id=user.id,
            conversation_id=payload.conversation_id,
            deleted=False
        )
        if checking is False:
            pass

        self.add(Message(
            text=payload.text,
            sender_id=user.id,
            conversation_id=payload.conversation_id,
            reply_id=payload.reply_id,
        ))
        await self.commit()
        await ws.send_json({"success": True, "message": "Message sent"})
