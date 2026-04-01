import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import Conversation
from models import User
from resources.managers.ws.dispatcher import WSDispatcher
from . import schemas

dp = WSDispatcher()


@dp.command("get_chats")
async def handle_chats(
        websocket: WebSocket,
        user: User,
):
    async with db_helper.session() as session:
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
        res = (await session.execute(stmt)).scalars().all()
    data = schemas.ConversationModelResponse(data=res).model_dump_json()
    await websocket.send_text(data)
