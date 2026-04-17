__all__ = (
    'Server',
)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check
from starlette.staticfiles import StaticFiles

from api.routers import __routes__ as api_routes, __ws_routes__ as ws_routes
from config import APP_SETTINGS
from .events import on_startup, on_shutdown


class Server:
    __app: FastAPI

    def __init__(self, app: FastAPI):
        self.__app = app
        self.__register_routes(app)
        self.__register_ws_routes(app)
        self.__register_middlewares(app)
        self.__register_media_files(app)
        self.__register_static_files(app)
        self.__register_pagination(app)

    def get_app(self):
        return self.__app

    @staticmethod
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await on_startup()
        yield
        await on_shutdown()

    @staticmethod
    def __register_routes(app):
        api_routes.register_routes(app, prefix=APP_SETTINGS.API_V1_PREFIX)

    @staticmethod
    def __register_ws_routes(app):
        ws_routes.register_routes(app, prefix=APP_SETTINGS.WS_PREFIX)

    @staticmethod
    def __register_middlewares(app: FastAPI):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @staticmethod
    def __register_media_files(app: FastAPI):
        app.mount(
            f'/{APP_SETTINGS.MEDIA_URL}',
            StaticFiles(directory=f"{APP_SETTINGS.MEDIA_DIR}", check_dir=False),
            name="media",
        )

    @staticmethod
    def __register_static_files(app: FastAPI):
        app.mount(
            f'/{APP_SETTINGS.STATIC_URL}',
            StaticFiles(directory=f"{APP_SETTINGS.STATIC_DIR}", check_dir=False),
            name="static",
        )

    @staticmethod
    def __register_pagination(app: FastAPI):
        add_pagination(app)
        disable_installed_extensions_check()



