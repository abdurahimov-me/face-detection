from config.qdrant import qdrant_db
from resources.detection.data import TrackIdentity
from resources.repositories import FacesRepository


async def ensure_faces_collection() -> None:
    await FacesRepository(qdrant_db.client).ensure_collection()


async def resolve_identity(embedding: list[float]) -> TrackIdentity:
    match = await FacesRepository(qdrant_db.client).identify(embedding)
    if match is None:
        return TrackIdentity()
    payload = match.payload or {}
    return TrackIdentity(
        user_id=str(payload.get('user_id')) if payload.get('user_id') is not None else None,
        full_name=str(payload.get('full_name') or "Noma'lum"),
        score=float(match.score),
    )
