import sqlalchemy as sa
from fastapi import WebSocket

from models import User, Conversation, Member
from resources.services import BaseWSService
from . import schemas


class ChatsService(BaseWSService):

    async def get_chats(
            self,
            ws: WebSocket,
            user: User,
    ):
        stmt = (
            sa.select(Conversation)
            # .join(Member, Member.conversation_id == Conversation.id, isouter=True)
            # .where(
            #     Member.user_id == user.id,
            #     Member.left_at.is_(None)
            # )
        )
        res = (await self.execute(stmt)).scalars().all()
        data = schemas.ConversationModelResponse(data=res).model_dump_json()
        await ws.send_text(data)
