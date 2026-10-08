from __future__ import annotations

import typing as t
from qdrant_client import AsyncQdrantClient, models


PointId = int | str
Vector = t.List[float] | t.Dict[str, t.List[float]]


class BaseRepository:
    collection_name: str

    def __init__(self, qdrant_client: AsyncQdrantClient):
        if not getattr(self, 'collection_name', None):
            raise ValueError('Repository collection_name must be set')
        self.qdrant_client = qdrant_client

    async def collection_exists(self) -> bool:
        return await self.qdrant_client.collection_exists(self.collection_name)

    async def create_collection(
        self,
        vectors_config: models.VectorParams | t.Dict[str, models.VectorParams],
    ) -> bool:
        if await self.collection_exists():
            return False
        return await self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=vectors_config,
        )

    async def delete_collection(self) -> bool:
        if not await self.collection_exists():
            return False
        return await self.qdrant_client.delete_collection(self.collection_name)

    async def get(self, point_id: PointId, *, with_vectors: bool = False) -> models.Record | None:
        records = await self.qdrant_client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
            with_payload=True,
            with_vectors=with_vectors,
        )
        return records[0] if records else None

    async def get_many(
        self, point_ids: t.Sequence[PointId], *, with_vectors: bool = False
    ) -> t.List[models.Record]:
        if not point_ids:
            return []
        return await self.qdrant_client.retrieve(
            collection_name=self.collection_name,
            ids=point_ids,
            with_payload=True,
            with_vectors=with_vectors,
        )

    async def list(
        self,
        *,
        limit: int = 100,
        offset: PointId | None = None,
        query_filter: models.Filter | None = None,
        with_vectors: bool = False,
    ) -> t.Tuple[t.List[models.Record], PointId | None]:
        if limit < 1:
            raise ValueError('limit must be positive')
        return await self.qdrant_client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=with_vectors,
        )

    async def create(
        self, point_id: PointId, vector: Vector, payload: t.Dict[str, t.Any] | None = None
    ) -> models.UpdateResult:
        if await self.get(point_id) is not None:
            raise ValueError(f'Point already exists: {point_id}')
        return await self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(id=point_id, vector=vector, payload=payload or {})],
            wait=True,
            update_mode=models.UpdateMode.INSERT_ONLY,
        )

    async def upsert(
        self, point_id: PointId, vector: Vector, payload: t.Dict[str, t.Any] | None = None
    ) -> models.UpdateResult:
        return await self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(id=point_id, vector=vector, payload=payload or {})],
            wait=True,
        )

    async def upsert_many(self, points: t.Sequence[models.PointStruct]) -> models.UpdateResult | None:
        if not points:
            return None
        return await self.qdrant_client.upsert(
            collection_name=self.collection_name, points=points, wait=True
        )

    async def update(
        self,
        point_id: PointId,
        *,
        vector: Vector | None = None,
        payload: t.Dict[str, t.Any] | None = None,
    ) -> models.UpdateResult:
        if vector is None and payload is None:
            raise ValueError('vector or payload is required')
        current = await self.get(point_id, with_vectors=True)
        if current is None:
            raise LookupError(f'Point not found: {point_id}')
        merged_payload = {**(current.payload or {}), **(payload or {})}
        current_vector = vector if vector is not None else current.vector
        if current_vector is None:
            raise ValueError(f'Point has no vector: {point_id}')
        return await self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(id=point_id, vector=current_vector, payload=merged_payload)],
            wait=True,
            update_mode=models.UpdateMode.UPDATE_ONLY,
        )

    async def delete(self, point_id: PointId) -> bool:
        if await self.get(point_id) is None:
            return False
        await self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=[point_id]),
            wait=True,
        )
        return True

    async def search(
        self,
        vector: t.List[float],
        *,
        limit: int = 10,
        score_threshold: float | None = None,
        query_filter: models.Filter | None = None,
        with_vectors: bool = False,
    ) -> t.List[models.ScoredPoint]:
        if limit < 1:
            raise ValueError('limit must be positive')
        result = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=with_vectors,
        )
        return result.points

    async def search_batch(
        self,
        vectors: t.Sequence[t.List[float]],
        *,
        limit: int = 10,
        score_threshold: float | None = None,
        query_filter: models.Filter | None = None,
        with_vectors: bool = False,
    ) -> t.List[t.List[models.ScoredPoint]]:
        if not vectors:
            return []
        if limit < 1:
            raise ValueError('limit must be positive')
        responses = await self.qdrant_client.query_batch_points(
            collection_name=self.collection_name,
            requests=[
                models.QueryRequest(
                    query=vector,
                    filter=query_filter,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vector=with_vectors,
                )
                for vector in vectors
            ],
        )
        return [response.points for response in responses]

    async def count(self, *, query_filter: models.Filter | None = None) -> int:
        result = await self.qdrant_client.count(
            collection_name=self.collection_name,
            count_filter=query_filter,
            exact=True,
        )
        return result.count
