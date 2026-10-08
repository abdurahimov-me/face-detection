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
from pydantic import Field, computed_field
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
    MODEL_NAME: str = "antelopev2"
    FACES_COLLECTION_NAME: str = 'faces'
    EMBEDDING_SIZE: int = 512
    MATCH_THRESHOLD: float = 0.55
    MATCH_MARGIN: float = 0.04
    MATCH_VOTES_REQUIRED: int = 2
    MATCH_CANDIDATES: int = 2
    DETECTION_SIZE: tuple = (320, 320)
    ANALYSIS_INTERVAL_SECONDS: float = 0.15
    RECOGNITION_SAMPLES: int = 3
    RECOGNITION_SAMPLE_INTERVAL_SECONDS: float = 0.25
    UNKNOWN_RETRY_INITIAL_SECONDS: float = 1.0
    UNKNOWN_RETRY_MAX_SECONDS: float = 8.0
    UNKNOWN_CLUSTER_THRESHOLD: float = 0.65
    MAX_IMAGE_BYTES: float = 8 * 1024 * 1024
    MIN_FACE_SIZE: int = 80
    ENROLLMENT_SAMPLES: int = 7
    ENROLLMENT_INTERVAL_SECONDS: float = 0.45
    ENROLLMENT_TIMEOUT_SECONDS: int = 45
    MIN_SHARPNESS: float = 45.0
    MIN_SAMPLE_SIMILARITY: float = 0.65
    MIN_DUPLICATE_SIMILARITY: float = 0.75
    ALLOWED_IMAGE_TYPES: set[str] = {'image/jpeg', 'image/png', 'image/webp'}

    @computed_field
    def FACE_IMAGES_DIR(self) -> Path:
        path = Path(self.MEDIA_DIR) / 'faces'
        path.mkdir(parents=True, exist_ok=True)
        return path


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
