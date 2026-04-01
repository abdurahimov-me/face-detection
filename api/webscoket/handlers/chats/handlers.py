from fastapi import WebSocket, Depends

from models import User
from resources.managers.ws.dispatcher import WSDispatcher
from . import services, schemas

dp = WSDispatcher()


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
        payload: schemas.SendMessageModel,
        user: User,
        service: services.ChatsService = Depends(services.ChatsService.create_service("db")),
):
    return await service.send_message(ws=websocket, user=user, payload=payload)
