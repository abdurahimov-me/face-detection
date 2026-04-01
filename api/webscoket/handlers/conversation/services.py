from fastapi import WebSocket

from models import User, Member, Message
from resources.services import BaseWSService
from . import schemas
import sqlalchemy as sa

class ChatsService(BaseWSService):

    async def send_message(
            self,
            ws: WebSocket,
            user: User,
            payload: schemas.SendMessageModel
    ):
        query = sa.select(sa.exists().where(
            Member.user_id == user.id,
            Member.conversation_id == payload.conversation_id,
            Member.deleted.is_(False),
        ))
        checking = await self.execute(query)
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
