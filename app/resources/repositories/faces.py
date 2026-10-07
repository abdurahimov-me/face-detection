from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import AsyncQdrantClient, models

from config import APP_SETTINGS
from config.qdrant import BaseRepository


class FacesRepository(BaseRepository):

    collection_name = APP_SETTINGS.FACES_COLLECTION_NAME

    def __init__(self, qdrant_client: AsyncQdrantClient):
        super().__init__(qdrant_client)

    @staticmethod
    def point_id_for_user(user_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, f'face-user:{user_id}'))

    async def ensure_collection(self) -> bool:
        return await self.create_collection(
            models.VectorParams(
                size=APP_SETTINGS.EMBEDDING_SIZE,
                distance=models.Distance.COSINE,
            )
        )

    async def get_by_user_id(
        self, user_id: str, *, with_vectors: bool = False
    ) -> models.Record | None:
        return await self.get(
            self.point_id_for_user(user_id),
            with_vectors=with_vectors,
        )

    async def user_id_exists(self, user_id: str) -> bool:
        return await self.get_by_user_id(user_id) is not None

    async def create_face(
        self,
        user_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> models.UpdateResult:
        return await self.create(
            self.point_id_for_user(user_id),
            vector,
            payload,
        )

    async def update_face(
        self,
        user_id: str,
        *,
        vector: list[float] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> models.UpdateResult:
        return await self.update(
            self.point_id_for_user(user_id),
            vector=vector,
            payload=payload,
        )

    async def delete_by_user_id(self, user_id: str) -> bool:
        return await self.delete(self.point_id_for_user(user_id))

    async def list_all(self, *, page_size: int = 100) -> list[models.Record]:
        points: list[models.Record] = []
        offset = None
        while True:
            page, offset = await self.list(
                limit=page_size,
                offset=offset,
                with_vectors=False,
            )
            points.extend(page)
            if offset is None:
                return points

    async def find_similar(
        self,
        vector: list[float],
        *,
        limit: int = 1,
        score_threshold: float | None = None,
    ) -> list[models.ScoredPoint]:
        return await self.search(
            vector,
            limit=limit,
            score_threshold=score_threshold,
        )

    async def find_duplicate(self, vector: list[float]) -> models.ScoredPoint | None:
        matches = await self.find_similar(
            vector,
            limit=1,
            score_threshold=APP_SETTINGS.MIN_DUPLICATE_SIMILARITY,
        )
        return matches[0] if matches else None

    async def identify(self, vector: list[float]) -> models.ScoredPoint | None:
        matches = await self.find_similar(
            vector,
            limit=1,
            score_threshold=APP_SETTINGS.MATCH_THRESHOLD,
        )
        return matches[0] if matches else None
