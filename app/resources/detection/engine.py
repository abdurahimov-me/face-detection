import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass

import numpy as np
import supervision as sv
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError
from insightface.app import FaceAnalysis
from insightface.app.common import Face
from qdrant_client import models
from trackers import ByteTrackTracker
from config.settings import APP_SETTINGS

from config.qdrant import qdrant_db


logger = logging.getLogger(__name__)


_engine: FaceAnalysis | None = None
_engine_init_lock = threading.Lock()
_inference_lock = threading.Lock()
_peer_connections: set[RTCPeerConnection] = set()


def get_face_engine() -> FaceAnalysis:
    global _engine
    if _engine is None:
        with _engine_init_lock:
            if _engine is None:
                engine = FaceAnalysis(
                    name=APP_SETTINGS.MODEL_NAME,
                    allowed_modules=['detection', 'recognition'],
                    providers=['CPUExecutionProvider'],
                )
                engine.prepare(
                    ctx_id=-1,
                    det_thresh=0.25,
                    det_size=APP_SETTINGS.DETECTION_SIZE,
                )
                _engine = engine
    return _engine


def analyze_face_image(image: np.ndarray) -> list[Face]:
    engine = get_face_engine()
    with _inference_lock:
        return engine.get(image)


@dataclass
class TrackIdentity:
    user_id: str | None = None
    full_name: str = "Noma'lum"
    score: float | None = None


class RecognitionSession:
    def __init__(self) -> None:
        self.tracker = ByteTrackTracker(
            frame_rate=7.0,
            lost_track_buffer=30,
            track_activation_threshold=0.5,
            minimum_consecutive_frames=2,
            minimum_iou_threshold=0.1,
            high_conf_det_threshold=0.5,
        )
        self.identities: dict[int, TrackIdentity] = {}

    def analyze(self, image: np.ndarray) -> list[dict]:
        engine = get_face_engine()
        with _inference_lock:
            bboxes, keypoints = engine.det_model.detect(image)

        data = {}
        if keypoints is not None:
            data['face_keypoints'] = keypoints
        detections = sv.Detections(
            xyxy=bboxes[:, :4].astype(np.float32),
            confidence=bboxes[:, 4].astype(np.float32),
            data=data,
        )
        tracked = self.tracker.update(detections)
        results: list[dict] = []

        for index in range(len(tracked)):
            track_id = int(tracked.tracker_id[index])
            if track_id < 0:
                continue

            item = {
                'track_id': track_id,
                'bbox': [float(value) for value in tracked.xyxy[index]],
                'embedding': None,
            }
            if track_id not in self.identities:
                self.identities[track_id] = TrackIdentity(full_name='Qidirilmoqda...')
                tracked_keypoints = tracked.data.get('face_keypoints')
                if tracked_keypoints is not None:
                    face = Face(
                        bbox=tracked.xyxy[index],
                        kps=tracked_keypoints[index],
                        det_score=float(tracked.confidence[index]),
                    )
                    with _inference_lock:
                        engine.models['recognition'].get(image, face)
                    item['embedding'] = face.normed_embedding.tolist()
            results.append(item)
        return results


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
                faces.append(
                    {
                        'track_id': tracked_face['track_id'],
                        'user_id': identity.user_id,
                        'full_name': identity.full_name,
                        'score': identity.score,
                        'bbox': tracked_face['bbox'],
                        'frame_width': image.shape[1],
                        'frame_height': image.shape[0],
                    }
                )

            channel = channel_holder.get('channel')
            if channel is not None and channel.readyState == 'open':
                channel.send(
                    json.dumps(
                        {
                            'faces': faces,
                            'processing_ms': (time.perf_counter() - started) * 1000,
                        }
                    )
                )
    except MediaStreamError:
        logger.info('WebRTC video track ended')
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception('WebRTC video processing failed')


async def create_webrtc_answer(sdp: str, description_type: str) -> RTCSessionDescription:
    await ensure_faces_collection()
    peer = RTCPeerConnection()
    _peer_connections.add(peer)
    session = RecognitionSession()
    channel_holder: dict = {}
    video_tasks: set[asyncio.Task] = set()

    @peer.on('datachannel')
    def on_datachannel(channel) -> None:
        if channel.label == 'detections':
            channel_holder['channel'] = channel

    @peer.on('track')
    def on_track(track) -> None:
        if track.kind == 'video':
            task = asyncio.create_task(consume_video(track, session, channel_holder))
            video_tasks.add(task)
            task.add_done_callback(video_tasks.discard)

    @peer.on('connectionstatechange')
    async def on_connectionstatechange() -> None:
        if peer.connectionState in {'failed', 'closed', 'disconnected'}:
            for task in video_tasks:
                task.cancel()
            await peer.close()
            _peer_connections.discard(peer)

    await peer.setRemoteDescription(
        RTCSessionDescription(sdp=sdp, type=description_type)
    )
    answer = await peer.createAnswer()
    await peer.setLocalDescription(answer)
    return peer.localDescription


async def create_enrollment_answer(
    sdp: str, description_type: str, user_id: str, full_name: str
) -> RTCSessionDescription:
    from api.faces.services import (
        EnrollmentSession,
        check_user_id_available,
        validate_user_fields,
    )

    user_id, full_name = validate_user_fields(user_id, full_name)
    await ensure_faces_collection()
    await check_user_id_available(user_id)
    peer = RTCPeerConnection()
    _peer_connections.add(peer)
    session = EnrollmentSession(user_id, full_name)
    channel_holder: dict = {}
    video_tasks: set[asyncio.Task] = set()

    @peer.on('datachannel')
    def on_datachannel(channel) -> None:
        if channel.label == 'enrollment':
            channel_holder['channel'] = channel

    @peer.on('track')
    def on_track(track) -> None:
        if track.kind == 'video':
            task = asyncio.create_task(session.consume(track, channel_holder))
            video_tasks.add(task)
            task.add_done_callback(video_tasks.discard)

    @peer.on('connectionstatechange')
    async def on_connectionstatechange() -> None:
        if peer.connectionState in {'failed', 'closed', 'disconnected'}:
            for task in video_tasks:
                task.cancel()
            await peer.close()
            _peer_connections.discard(peer)

    try:
        await peer.setRemoteDescription(
            RTCSessionDescription(sdp=sdp, type=description_type)
        )
        answer = await peer.createAnswer()
        await peer.setLocalDescription(answer)
        return peer.localDescription
    except Exception:
        await peer.close()
        _peer_connections.discard(peer)
        raise


async def close_peer_connections() -> None:
    peers = list(_peer_connections)
    _peer_connections.clear()
    await asyncio.gather(*(peer.close() for peer in peers), return_exceptions=True)
