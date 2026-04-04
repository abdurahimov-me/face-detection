import typing as t
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import APIRouter
from fastapi import FastAPI

from config import APP_SETTINGS

if t.TYPE_CHECKING:
    from resources.managers.ws.dispatcher import WSDispatcher
    from resources.managers.ws.manager import ChatWebSocketManager


@dataclass
class Routes:
    routers: Iterable[APIRouter]

    def register_routes(self, app: FastAPI, prefix=APP_SETTINGS.API_V1_PREFIX):
        for router in self.routers:
            app.include_router(router, prefix=prefix)


@dataclass
class WSDispatchers:
    dispatchers: Iterable["WSDispatcher"]

    def register_dispatchers(self, manager: "ChatWebSocketManager"):
        for handler in self.dispatchers:
            manager.include_handler(handler)
