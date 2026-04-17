__all__ = (
    'BASE_DIR',
    'EnvReader',
    'DB_SETTINGS',
    'APP_SETTINGS',
)

import os
import typing as t
from pathlib import Path

from dotenv import load_dotenv
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


class EnvReader(BaseSettings):
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = "ignore"


class APPSettings(EnvReader):
    VERSION: str = '1.0.0'
    API_V1_PREFIX: str = "/api/v1"
    WS_PREFIX: str = "/ws"
    PROJECT_NAME: str = "Logger"
    MEDIA_URL: str = 'media/'
    STATIC_URL: str = 'static/'
    MEDIA_DIR: t.ClassVar[str] = os.path.join(BASE_DIR, 'media')
    STATIC_DIR: t.ClassVar[str] = os.path.join(BASE_DIR, 'static')
    TIME_ZONE: str = 'Asia/Tashkent'
    SERVER_HOST: str = 'localhost'
    DEBUG: bool = True
    GRPC_HOST: str
    GRPC_PORT: int


class DBSettings(EnvReader):
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    ECHO: bool

    @property
    def URL(self) -> str:
        return str(PostgresDsn.build(
            scheme='postgresql+asyncpg',
            host=self.DB_HOST,
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            port=self.DB_PORT,
            path=self.DB_NAME,
        ))


DB_SETTINGS = DBSettings()
APP_SETTINGS = APPSettings()
