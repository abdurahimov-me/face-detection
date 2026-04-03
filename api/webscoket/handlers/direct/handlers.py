import typing as t

import sqlalchemy as sa
from fastapi import WebSocket

from config.db import db_helper
from models import Conversation, Message, MessageRead, Member
from models import User
from resources.managers.ws.dispatcher import WSDispatcher
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

