import typing as t

from config import APP_SETTINGS
from config.qdrant import qdrant_db
from resources.detection.data import TrackIdentity
from resources.repositories import FacesRepository


async def ensure_faces_collection() -> None:
    await FacesRepository(qdrant_db.client).ensure_collection()


async def resolve_identity(embeddings: t.List[t.List[float]]) -> TrackIdentity:
    results = await FacesRepository(qdrant_db.client).identify_batch(embeddings)
    votes: t.Dict[str, t.List] = {}
    for matches in results:
        if not matches:
            continue
        best = matches[0]
        if (
            len(matches) > 1
            and float(best.score) - float(matches[1].score) < APP_SETTINGS.MATCH_MARGIN
        ):
            continue
        payload = best.payload or {}
        user_id = payload.get('user_id')
        if user_id is None:
            continue
        votes.setdefault(str(user_id), []).append(best)

    if not votes:
        return TrackIdentity()
    user_id, matches = max(votes.items(), key=lambda item: len(item[1]))
    if len(matches) < APP_SETTINGS.MATCH_VOTES_REQUIRED:
        return TrackIdentity()
    payload = matches[0].payload or {}
    return TrackIdentity(
        user_id=user_id,
        full_name=str(payload.get('full_name') or "Noma'lum"),
        score=sum(float(match.score) for match in matches) / len(matches),
    )
