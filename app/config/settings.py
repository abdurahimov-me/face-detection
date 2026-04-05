__all__ = (
    'BASE_DIR',
    'EnvReader',
    'DB_SETTINGS',
    'REDIS_SETTINGS',
    'AWS_SETTINGS',
    'APP_SETTINGS',
    'JWT_SETTINGS',
)

import os
from datetime import timedelta
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from pydantic import PostgresDsn, RedisDsn
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
    PROJECT_NAME: str = "HR CHAT"
    MEDIA_URL: str = 'media/'
    STATIC_URL: str = 'static/'
    MEDIA_DIR: ClassVar[str] = os.path.join(BASE_DIR, 'media')
    STATIC_DIR: ClassVar[str] = os.path.join(BASE_DIR, 'static')
    TIME_ZONE: str = 'Asia/Tashkent'
    SERVER_HOST: str = 'localhost'
    DEBUG: bool = True
    FERNET_SECRET_KEY: str


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


class RedisSettings(EnvReader):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

    @property
    def URL(self) -> str:
        return str(RedisDsn.build(
            scheme='redis',
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=f"/{self.REDIS_DB}",
        ))


class EmailSettings(EnvReader):
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_PASSWORD: str
    EMAIL: str


class AWSSettings(EnvReader):
    AWS_ACCESS_KEY_ID: str = None
    AWS_SECRET_ACCESS_KEY: str = None
    AWS_BUCKET_NAME: str = None
    AWS_REGION_NAME: str = None
    AWS_ENDPOINT_URL: str = None
    CDN_URL: str = None


class JWTSettings(BaseSettings):
    ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str
    JWT_PAYLOAD_FIELDS: tuple = ('id',)
    ACCESS_TOKEN_EXPIRE: timedelta = timedelta(days=10)


DB_SETTINGS = DBSettings()
REDIS_SETTINGS = RedisSettings()
AWS_SETTINGS = AWSSettings()
APP_SETTINGS = APPSettings()
JWT_SETTINGS = JWTSettings()
