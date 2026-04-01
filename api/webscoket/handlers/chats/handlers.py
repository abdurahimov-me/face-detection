import typing as t

from fastapi import WebSocket, Depends
from pydantic import BaseModel

from models import User
from resources.managers.ws.dispatcher import WSDispatcher
from . import services

dp = WSDispatcher()


class Salom(BaseModel):
    text: str


@dp.command("get_chats")
async def handle_chats(
        websocket: WebSocket,
        user: User,
        service: services.ChatsService = Depends(services.ChatsService.create_service("db")),
):
    return await service.get_chats(ws=websocket, user=user)


@dp.command("send_message")
async def handle_chats(
        websocket: WebSocket,
        payload: t.Any,
        user: User
):
    await websocket.send_json({"msg": "Assalomu alaykum"})


@dp.command("accept_payload")
async def handle_chats(
        websocket: WebSocket,
        payload: t.Any,
        user: User
):
    await websocket.send_json({"payload": payload})
