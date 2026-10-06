__all__ = (
    'BASE_DIR',
    'EnvReader',
    'APP_SETTINGS',
    'JWT_SETTINGS',
    'QDRANT_SETTINGS',
)

import os
import typing as t
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
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
    ROOT_PATH: str = ''
    DEBUG: bool = True


class JWTSettings(BaseSettings):
    ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str = 'local-development-secret'
    JWT_PAYLOAD_FIELDS: tuple = ('id',)
    ACCESS_TOKEN_EXPIRE: timedelta = timedelta(days=10)


class QdrantSettings(EnvReader):
    class Config(EnvReader.Config):
        env_prefix = 'QDRANT_'

    HOST: str = 'localhost'
    PORT: int = Field(default=6333, ge=1, le=65535)
    API_KEY: t.Optional[str] = None
    TIMEOUT: float = Field(default=5.0, gt=0)
    CONNECT_RETRIES: int = Field(default=30, ge=1)
    RETRY_DELAY: float = Field(default=1.0, ge=0)

JWT_SETTINGS = JWTSettings()
APP_SETTINGS = APPSettings()
QDRANT_SETTINGS = QdrantSettings()
