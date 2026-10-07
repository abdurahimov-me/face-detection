import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable

import numpy as np
import supervision as sv
from aiortc.mediastreams import MediaStreamError
from insightface.app.common import Face
from trackers import ByteTrackTracker

from config import APP_SETTINGS
from ..data import TrackIdentity
from ..engine import get_face_engine, inference_lock

logger = logging.getLogger(__name__)


class RecognitionSession:
    def __init__(
        self,
        identity_resolver: Callable[[list[float]], Awaitable[TrackIdentity]],
    ) -> None:
        self.identity_resolver = identity_resolver
        self.tracker = ByteTrackTracker(
            frame_rate=7.0,
            lost_track_buffer=30,
            track_activation_threshold=0.5,
            minimum_consecutive_frames=2,
            minimum_iou_threshold=0.1,
            high_conf_det_threshold=0.5,
        )
        self.identities: dict[int, TrackIdentity] = {}
        self.embedded_tracks: set[int] = set()

    async def consume_video(self, track, channel_holder: dict) -> None:
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
                tracked_faces = await asyncio.to_thread(self.analyze, image)

                for tracked_face in tracked_faces:
                    embedding = tracked_face.pop('embedding')
                    track_id = tracked_face['track_id']
                    if embedding is not None:
                        self.identities[track_id] = await self.identity_resolver(embedding)

                faces = []
                for tracked_face in tracked_faces:
                    identity = self.identities[tracked_face['track_id']]
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

    def analyze(self, image: np.ndarray) -> list[dict]:
        engine = get_face_engine()
        with inference_lock:
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
            if track_id not in self.embedded_tracks:
                tracked_keypoints = tracked.data.get('face_keypoints')
                if tracked_keypoints is not None:
                    face = Face(
                        bbox=tracked.xyxy[index],
                        kps=tracked_keypoints[index],
                        det_score=float(tracked.confidence[index]),
                    )
                    with inference_lock:
                        engine.models['recognition'].get(image, face)
                    if face.normed_embedding is not None:
                        item['embedding'] = face.normed_embedding.tolist()
                        self.embedded_tracks.add(track_id)
            results.append(item)
        return results
