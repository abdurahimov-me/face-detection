import asyncio
import logging
import typing as t

from qdrant_client import AsyncQdrantClient

from config import QDRANT_SETTINGS

logger = logging.getLogger(__name__)


class QdrantDatabase:

    def __init__(self):
        self._client: t.Optional[AsyncQdrantClient] = None

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            raise RuntimeError('Qdrant client is not connected')
        return self._client

    async def connect(self) -> None:
        if self._client is not None:
            return

        client = AsyncQdrantClient(
            host=QDRANT_SETTINGS.HOST,
            port=QDRANT_SETTINGS.PORT,
            api_key=QDRANT_SETTINGS.API_KEY or None,
            timeout=QDRANT_SETTINGS.TIMEOUT,
        )

        for attempt in range(1, QDRANT_SETTINGS.CONNECT_RETRIES + 1):
            try:
                await client.get_collections()
                self._client = client
                logger.info(
                    'Connected to Qdrant at %s:%s',
                    QDRANT_SETTINGS.HOST,
                    QDRANT_SETTINGS.PORT,
                )
                return
            except Exception:
                if attempt == QDRANT_SETTINGS.CONNECT_RETRIES:
                    await client.close()
                    logger.exception(
                        'Could not connect to Qdrant at %s:%s',
                        QDRANT_SETTINGS.HOST,
                        QDRANT_SETTINGS.PORT,
                    )
                    raise

                logger.warning(
                    'Qdrant is not ready (attempt %s/%s); retrying in %s seconds',
                    attempt,
                    QDRANT_SETTINGS.CONNECT_RETRIES,
                    QDRANT_SETTINGS.RETRY_DELAY,
                )
                await asyncio.sleep(QDRANT_SETTINGS.RETRY_DELAY)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info('Disconnected from Qdrant')


qdrant_db = QdrantDatabase()
