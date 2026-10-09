import typing as t

from config import APP_SETTINGS
from config.qdrant import qdrant_db
from resources.detection.data import TrackIdentity
from resources.repositories import FacesRepository


async def ensure_faces_collection() -> None:
    await FacesRepository(qdrant_db.client).ensure_collection()


async def resolve_identity(embeddings: t.List[t.List[float]]) -> TrackIdentity:
    identities = await resolve_identities([embeddings])
    return identities[0]


async def resolve_identities(
        embedding_groups: t.List[t.List[t.List[float]]],
) -> t.List[TrackIdentity]:
    group_sizes = [len(group) for group in embedding_groups]
    vectors = [vector for group in embedding_groups for vector in group]
    if not vectors:
        return [TrackIdentity() for _ in embedding_groups]

    batch_results = await FacesRepository(qdrant_db.client).identify_batch(vectors)
    identities: t.List[TrackIdentity] = []
    offset = 0
    for group_size in group_sizes:
        results = batch_results[offset:offset + group_size]
        offset += group_size
        identities.append(_vote_identity(results))
    return identities


def _vote_identity(results: t.List[t.List]) -> TrackIdentity:
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
