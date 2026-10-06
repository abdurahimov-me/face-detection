import asyncio
import json
import logging
import time

from aiortc.mediastreams import MediaStreamError
from qdrant_client import models

from config.qdrant import qdrant_db
from config.settings import APP_SETTINGS
from resources.detection.data import TrackIdentity
from resources.detection.sessions.recognation import RecognitionSession


logger = logging.getLogger(__name__)


async def ensure_faces_collection() -> None:
    client = qdrant_db.client
    collections = await client.get_collections()
    if APP_SETTINGS.FACES_COLLECTION_NAME not in {item.name for item in collections.collections}:
        await client.create_collection(
            collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=APP_SETTINGS.EMBEDDING_SIZE,
                distance=models.Distance.COSINE,
            ),
        )


async def resolve_identity(embedding: list[float]) -> TrackIdentity:
    result = await qdrant_db.client.query_points(
        collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
        query=embedding,
        limit=1,
        score_threshold=APP_SETTINGS.MATCH_THRESHOLD,
        with_payload=True,
    )
    if not result.points:
        return TrackIdentity()
    match = result.points[0]
    payload = match.payload or {}
    return TrackIdentity(
        user_id=str(payload.get('user_id')) if payload.get('user_id') is not None else None,
        full_name=str(payload.get('full_name') or "Noma'lum"),
        score=float(match.score),
    )


async def consume_video(track, session: RecognitionSession, channel_holder: dict) -> None:
    last_analysis = 0.0
    try:
        while True:
            frame = await track.recv()
            now = time.monotonic()
            if now - last_analysis < APP_SETTINGS.ANALYSIS_INTERVAL_SECONDS:
                continue
            last_analysis = now
            started = time.perf_counter()
            image = frame.to_ndarray(format='bgr24')
            tracked_faces = await asyncio.to_thread(session.analyze, image)

            for tracked_face in tracked_faces:
                embedding = tracked_face.pop('embedding')
                track_id = tracked_face['track_id']
                if embedding is not None:
                    session.identities[track_id] = await resolve_identity(embedding)

            faces = []
            for tracked_face in tracked_faces:
                identity = session.identities[tracked_face['track_id']]
                faces.append({
                    'track_id': tracked_face['track_id'],
                    'user_id': identity.user_id,
                    'full_name': identity.full_name,
                    'score': identity.score,
                    'bbox': tracked_face['bbox'],
                    'frame_width': image.shape[1],
                    'frame_height': image.shape[0],
                })

            channel = channel_holder.get('channel')
            if channel is not None and channel.readyState == 'open':
                channel.send(json.dumps({
                    'faces': faces,
                    'processing_ms': (time.perf_counter() - started) * 1000,
                }))
    except MediaStreamError:
        logger.info('WebRTC video track ended')
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception('WebRTC video processing failed')
