import logging
import typing as t

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import db_helper
from integrations.grpc.services import user_grpc_service
from models import User
from resources.managers.ws.manager import chat_ws_manager
from utils import Payload
from utils.jwt import decode_jwt
from utils.routes import WSDispatchers
from .handlers import (
    chats,
    conversation,
    receive_message,
    group,
    profile
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

__ws_dispatchers__ = WSDispatchers(
    dispatchers=(
        chats.dp,
        group.dp,
        conversation.dp,
        receive_message.dp,
        profile.dp,
    )
)


def _parse_token(
        token: str
) -> t.Tuple[t.Optional[str], t.Optional["Payload"]]:
    try:

        payload = decode_jwt(token)
        return None, Payload.from_dict(payload)

    except jwt.ExpiredSignatureError:

        return "Token expired", None

    except (jwt.InvalidTokenError, jwt.DecodeError):
        return "Could not validate credentials", None


@router.websocket("/connect")
async def user_websocket(
        ws: WebSocket,
):
    if token := ws.query_params.get("token"):
        text, payload = _parse_token(token)
        if text:
            return await ws.close(code=1008)
    else:
        return await ws.close(code=1008)

    tenant = payload.tenant
    user_id = payload.user_id
    user_data = await user_grpc_service.get_user(int(user_id), tenant)

    if user_data is None:
        return await ws.close(code=1008)

    async with db_helper.session() as session:
        session: AsyncSession

        user, _ = await User.repo.db_get_or_create(session, tenant=tenant, user_id=user_id)
        user: User
        user.first_name = user_data.first_name
        user.last_name = user_data.last_name
        user.face = user_data.face
        user.extra_data = {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "face": user_data.face,
            "middle_name": user_data.middle_name,
            "username": user_data.username,
        }
        await session.commit()

    conn_id = user.conn_id
    await chat_ws_manager.connect(conn_id, ws)

    try:
        while True:
            message = await ws.receive_json()
            command = message.get("command")
            payload = message.get("payload")
            request_id = message.get("request_id")
            if not command:
                await chat_ws_manager.send_error(websocket=ws, message='You should provide message type')
                continue

            if ("payload" in message) and not payload:
                await chat_ws_manager.send_error(websocket=ws, message='You should provide payload')
                continue

            if not (func := chat_ws_manager.get_command_func(command)):
                logger.error(f"No Command [{command}] exists")
                await chat_ws_manager.send_error(websocket=ws, message=f"Command: {command} was not found")
                continue

            await chat_ws_manager.call_command(
                request_id=request_id,
                command=command,
                websocket=ws,
                user=user,
                payload=payload,
            )

    except WebSocketDisconnect:
        logger.info("Web socket disconnected")
        return await chat_ws_manager.disconnect(conn_id)
