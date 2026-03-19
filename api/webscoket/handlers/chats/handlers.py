import typing as t

from fastapi import WebSocket, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import get_db
from models import User
from resources.managers.ws.dispatcher import WSDispatcher

dp = WSDispatcher()

class Salom(BaseModel):
    text: str

@dp.command("get_chats")
async def handle_chats(
        websocket: WebSocket,
        payload: Salom,
):
    await websocket.send_json({"salom": "asdasdas"})


@dp.command("start")
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
