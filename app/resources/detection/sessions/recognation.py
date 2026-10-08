import asyncio
import base64
import json
import logging
import time
from collections.abc import Awaitable, Callable

import cv2
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
        identity_resolver: Callable[[list[list[float]]], Awaitable[TrackIdentity]],
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
        self.face_images: dict[int, str] = {}
        self.best_quality: dict[int, float] = {}
        self.embedding_samples: dict[int, list[np.ndarray]] = {}
        self.last_sample_at: dict[int, float] = {}
        self.next_retry_at: dict[int, float] = {}
        self.retry_delays: dict[int, float] = {}
        self.search_tasks: dict[int, asyncio.Task[None]] = {}
        self.identity_keys: dict[int, str] = {}
        self.unknown_embeddings: dict[str, np.ndarray] = {}
        self.unknown_counts: dict[str, int] = {}
        self.unknown_sequence = 0
        self.identity_tracks: dict[str, set[int]] = {}
        self.identity_best_quality: dict[str, float] = {}
        self.identity_best_images: dict[str, str] = {}

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
                    quality = tracked_face.pop('quality')
                    face_image = tracked_face.pop('candidate_image')
                    self.identities.setdefault(
                        track_id,
                        TrackIdentity(full_name='Qidirilmoqda...'),
                    )
                    if face_image is not None and quality > self.best_quality.get(track_id, 0.0):
                        self.best_quality[track_id] = quality
                        self.face_images[track_id] = face_image
                        identity_key = self.identity_keys.get(track_id)
                        if identity_key is not None:
                            self._update_identity_snapshot(track_id, identity_key)
                    if embedding is not None:
                        samples = self.embedding_samples.setdefault(track_id, [])
                        samples.append(np.asarray(embedding, dtype=np.float32))
                        self.last_sample_at[track_id] = now
                        if (
                            len(samples) >= APP_SETTINGS.RECOGNITION_SAMPLES
                            and track_id not in self.search_tasks
                        ):
                            self.next_retry_at[track_id] = float('inf')
                            sample_batch = [
                                sample.tolist()
                                for sample in samples[-APP_SETTINGS.RECOGNITION_SAMPLES:]
                            ]
                            task = asyncio.create_task(
                                self._resolve_track(track_id, sample_batch)
                            )
                            self.search_tasks[track_id] = task

                faces = []
                for tracked_face in tracked_faces:
                    track_id = tracked_face['track_id']
                    identity = self.identities[track_id]
                    identity_key = self.identity_keys.get(track_id)
                    faces.append({
                        'track_id': track_id,
                        'user_id': identity.user_id,
                        'full_name': identity.full_name,
                        'score': identity.score,
                        'identity_key': identity_key,
                        'track_count': len(self.identity_tracks.get(identity_key, set())),
                        'face_image': (
                            self.identity_best_images.get(identity_key)
                            if identity_key is not None
                            else self.face_images.get(track_id)
                        ),
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
        finally:
            tasks = list(self.search_tasks.values())
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self.search_tasks.clear()

    async def _resolve_track(
        self,
        track_id: int,
        embeddings: list[list[float]],
    ) -> None:
        try:
            identity = await self.identity_resolver(embeddings)
            self.identities[track_id] = identity
            self.embedding_samples.pop(track_id, None)
            if identity.user_id is None:
                mean = np.mean(np.asarray(embeddings, dtype=np.float32), axis=0)
                norm = float(np.linalg.norm(mean))
                if norm > 0:
                    mean = mean / norm
                identity_key = self._unknown_identity_key(
                    track_id,
                    mean,
                )
                self._assign_identity_key(track_id, identity_key)
                delay = self.retry_delays.get(
                    track_id,
                    APP_SETTINGS.UNKNOWN_RETRY_INITIAL_SECONDS,
                )
                self.next_retry_at[track_id] = time.monotonic() + delay
                self.retry_delays[track_id] = min(
                    delay * 2,
                    APP_SETTINGS.UNKNOWN_RETRY_MAX_SECONDS,
                )
            else:
                self._assign_identity_key(track_id, f'user:{identity.user_id}')
                self.next_retry_at[track_id] = float('inf')
                self.retry_delays.pop(track_id, None)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Recognition search failed for track #%s', track_id)
            self.identities[track_id] = TrackIdentity()
            self.embedding_samples.pop(track_id, None)
            self.next_retry_at[track_id] = (
                time.monotonic() + APP_SETTINGS.UNKNOWN_RETRY_INITIAL_SECONDS
            )
        finally:
            self.search_tasks.pop(track_id, None)

    def _assign_identity_key(self, track_id: int, identity_key: str) -> None:
        previous_key = self.identity_keys.get(track_id)
        if previous_key is not None and previous_key != identity_key:
            previous_tracks = self.identity_tracks.get(previous_key)
            if (
                previous_tracks is not None
                and previous_key.startswith('unknown:')
                and identity_key.startswith('user:')
            ):
                target_tracks = self.identity_tracks.setdefault(identity_key, set())
                target_tracks.update(previous_tracks)
                for previous_track_id in previous_tracks:
                    self.identity_keys[previous_track_id] = identity_key
                previous_quality = self.identity_best_quality.get(previous_key, 0.0)
                if previous_quality > self.identity_best_quality.get(identity_key, 0.0):
                    self.identity_best_quality[identity_key] = previous_quality
                    previous_image = self.identity_best_images.get(previous_key)
                    if previous_image is not None:
                        self.identity_best_images[identity_key] = previous_image
                self.identity_tracks.pop(previous_key, None)
                self.identity_best_quality.pop(previous_key, None)
                self.identity_best_images.pop(previous_key, None)
                self.unknown_embeddings.pop(previous_key, None)
                self.unknown_counts.pop(previous_key, None)
            elif previous_tracks is not None:
                previous_tracks.discard(track_id)

        self.identity_keys[track_id] = identity_key
        self.identity_tracks.setdefault(identity_key, set()).add(track_id)
        self._update_identity_snapshot(track_id, identity_key)

    def _update_identity_snapshot(self, track_id: int, identity_key: str) -> None:
        image = self.face_images.get(track_id)
        quality = self.best_quality.get(track_id)
        if image is None or quality is None:
            return
        if quality > self.identity_best_quality.get(identity_key, 0.0):
            self.identity_best_quality[identity_key] = quality
            self.identity_best_images[identity_key] = image

    def _unknown_identity_key(self, track_id: int, embedding: np.ndarray) -> str:
        norm = float(np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / norm

        key = self.identity_keys.get(track_id)
        if key not in self.unknown_embeddings:
            key = None
            best_score = -1.0
            for candidate_key, candidate_embedding in self.unknown_embeddings.items():
                score = float(np.dot(embedding, candidate_embedding))
                if score > best_score:
                    best_score = score
                    key = candidate_key
            if best_score < APP_SETTINGS.UNKNOWN_CLUSTER_THRESHOLD:
                self.unknown_sequence += 1
                key = f'unknown:{self.unknown_sequence}'

        count = self.unknown_counts.get(key, 0)
        current = self.unknown_embeddings.get(key)
        if current is None:
            prototype = embedding
        else:
            prototype = (current * count + embedding) / (count + 1)
            prototype_norm = float(np.linalg.norm(prototype))
            if prototype_norm > 0:
                prototype = prototype / prototype_norm
        self.unknown_embeddings[key] = prototype
        self.unknown_counts[key] = count + 1
        return key

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

            bbox = tracked.xyxy[index]
            tracked_keypoints = tracked.data.get('face_keypoints')
            face_keypoints = (
                tracked_keypoints[index] if tracked_keypoints is not None else None
            )
            confidence = float(tracked.confidence[index])
            quality = self._quality_score(image, bbox, face_keypoints, confidence)
            item = {
                'track_id': track_id,
                'bbox': [float(value) for value in bbox],
                'embedding': None,
                'quality': quality or 0.0,
                'candidate_image': None,
            }
            if quality is not None and quality > self.best_quality.get(track_id, 0.0):
                item['candidate_image'] = self._encode_face_image(image, bbox)

            identity = self.identities.get(track_id)
            is_known = identity is not None and identity.user_id is not None
            now = time.monotonic()
            can_sample = (
                not is_known
                and track_id not in self.search_tasks
                and now >= self.next_retry_at.get(track_id, 0.0)
                and now - self.last_sample_at.get(track_id, 0.0)
                >= APP_SETTINGS.RECOGNITION_SAMPLE_INTERVAL_SECONDS
            )
            if quality is not None and can_sample and face_keypoints is not None:
                face = Face(
                    bbox=bbox,
                    kps=face_keypoints,
                    det_score=confidence,
                )
                with inference_lock:
                    engine.models['recognition'].get(image, face)
                if face.normed_embedding is not None:
                    item['embedding'] = face.normed_embedding.tolist()
            results.append(item)
        return results

    @staticmethod
    def _quality_score(
        image: np.ndarray,
        bbox: np.ndarray,
        keypoints: np.ndarray | None,
        confidence: float,
    ) -> float | None:
        height, width = image.shape[:2]
        x1, y1, x2, y2 = bbox.astype(int)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)
        face_width, face_height = x2 - x1, y2 - y1
        face_size = min(face_width, face_height)
        if (
            face_size < APP_SETTINGS.MIN_FACE_SIZE
            or confidence < 0.5
            or keypoints is None
            or len(keypoints) < 3
        ):
            return None

        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if not 55 <= brightness <= 210 or sharpness < APP_SETTINGS.MIN_SHARPNESS:
            return None

        eye_tilt = abs(float(keypoints[0][1] - keypoints[1][1])) / face_height
        eyes_center_x = float(keypoints[0][0] + keypoints[1][0]) / 2
        nose_offset = abs(float(keypoints[2][0]) - eyes_center_x) / face_width
        if eye_tilt > 0.14 or nose_offset > 0.22:
            return None

        size_score = min(1.0, face_size / 180)
        sharpness_score = min(1.0, sharpness / 140)
        brightness_score = max(0.0, 1.0 - abs(brightness - 132) / 100)
        pose_score = max(0.0, 1.0 - eye_tilt / 0.14 - nose_offset / 0.22)
        return (
            confidence * 0.20
            + size_score * 0.20
            + sharpness_score * 0.30
            + brightness_score * 0.15
            + pose_score * 0.15
        )

    @staticmethod
    def _encode_face_image(image: np.ndarray, bbox: np.ndarray) -> str | None:
        height, width = image.shape[:2]
        x1, y1, x2, y2 = bbox.astype(int)
        padding_x = max(8, int((x2 - x1) * 0.18))
        padding_y = max(8, int((y2 - y1) * 0.18))
        x1 = max(0, x1 - padding_x)
        y1 = max(0, y1 - padding_y)
        x2 = min(width, x2 + padding_x)
        y2 = min(height, y2 + padding_y)
        if x2 <= x1 or y2 <= y1:
            return None

        crop = image[y1:y2, x1:x2]
        crop_height, crop_width = crop.shape[:2]
        scale = min(1.0, 160 / max(crop_width, crop_height))
        if scale < 1.0:
            crop = cv2.resize(
                crop,
                (max(1, round(crop_width * scale)), max(1, round(crop_height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        encoded, jpeg = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 72])
        if not encoded:
            return None
        value = base64.b64encode(jpeg.tobytes()).decode('ascii')
        return f'data:image/jpeg;base64,{value}'
