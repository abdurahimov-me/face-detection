from fastapi import WebSocket

from models import User, Member, Message
from resources.services import BaseWSService
from . import schemas


class ChatsService(BaseWSService):

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
