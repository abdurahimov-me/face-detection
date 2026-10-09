import base64
import math
import typing as t
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from insightface.app.common import Face
from trackers import ByteTrackTracker

from config import APP_SETTINGS
from resources.detection.engine import get_face_engine, inference_lock
from .data import VideoSample, VideoScanResult, VideoTrackResult, ActiveTrack


def scan_video(
        video_path: Path,
        progress_callback: t.Callable[[float], None],
) -> VideoScanResult:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError('Video faylini ochib bo‘lmadi.')

    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not math.isfinite(source_fps) or source_fps <= 0:
        source_fps = 25.0
    total_frames = max(0, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    frame_step = max(1, round(source_fps / APP_SETTINGS.VIDEO_ANALYSIS_FPS))
    analyzed_fps = source_fps / frame_step
    lost_steps = max(1, round(APP_SETTINGS.VIDEO_TRACK_LOST_SECONDS * analyzed_fps))
    tracker = ByteTrackTracker(
        frame_rate=analyzed_fps,
        lost_track_buffer=lost_steps,
        track_activation_threshold=0.5,
        minimum_consecutive_frames=2,
        minimum_iou_threshold=0.1,
        high_conf_det_threshold=0.5,
    )
    active: t.Dict[int, ActiveTrack] = {}
    completed: t.List[VideoTrackResult] = []
    source_frame = 0
    analyzed_frames = 0

    try:
        while capture.grab():
            source_frame += 1
            if total_frames:
                progress_callback(min(84.0, source_frame / total_frames * 84.0))
            if (source_frame - 1) % frame_step:
                continue
            success, image = capture.retrieve()
            if not success or image is None:
                continue

            analyzed_frames += 1
            timestamp = (source_frame - 1) / source_fps
            tracked_faces = _detect_and_track(image, tracker)
            seen: t.Set[int] = set()
            for tracked_face in tracked_faces:
                track_id = tracked_face['track_id']
                seen.add(track_id)
                state = active.get(track_id)
                if state is None:
                    state = ActiveTrack(
                        track_id=track_id,
                        start=timestamp,
                        end=timestamp,
                        last_seen_step=analyzed_frames,
                    )
                    active[track_id] = state
                state.end = timestamp
                state.last_seen_step = analyzed_frames
                _consider_sample(state, image, tracked_face, timestamp)

            stale = [
                track_id
                for track_id, state in active.items()
                if track_id not in seen
                   and analyzed_frames - state.last_seen_step > lost_steps
            ]
            for track_id in stale:
                completed.append(active.pop(track_id).finish())
    finally:
        capture.release()

    completed.extend(state.finish() for state in active.values())
    duration = source_frame / source_fps
    progress_callback(85.0)
    return VideoScanResult(
        duration=duration,
        analyzed_fps=analyzed_fps,
        processed_frames=analyzed_frames,
        tracks=completed,
    )


def _detect_and_track(
        image: np.ndarray,
        tracker: ByteTrackTracker,
) -> t.List[t.Dict[str, t.Any]]:
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
    tracked = tracker.update(detections)
    tracked_keypoints = tracked.data.get('face_keypoints')
    results: t.List[t.Dict[str, t.Any]] = []
    for index in range(len(tracked)):
        track_id = int(tracked.tracker_id[index])
        if track_id < 0:
            continue
        results.append({
            'track_id': track_id,
            'bbox': tracked.xyxy[index],
            'confidence': float(tracked.confidence[index]),
            'keypoints': (
                tracked_keypoints[index] if tracked_keypoints is not None else None
            ),
        })
    return results


def _consider_sample(
        state: ActiveTrack,
        image: np.ndarray,
        tracked_face: t.Dict[str, t.Any],
        timestamp: float,
) -> None:
    bbox = tracked_face['bbox']
    keypoints = tracked_face['keypoints']
    quality = _quality_score(
        image,
        bbox,
        keypoints,
        tracked_face['confidence'],
    )
    if state.best_image is None:
        state.best_image = _encode_face_image(image, bbox)
    if quality is None:
        return

    if quality > state.best_quality:
        state.best_quality = quality
        state.best_image = _encode_face_image(image, bbox)
    if timestamp - state.last_sample_at < APP_SETTINGS.VIDEO_SAMPLE_INTERVAL_SECONDS:
        return
    if (
            len(state.samples) >= APP_SETTINGS.RECOGNITION_SAMPLES
            and quality <= state.samples[-1].quality
    ):
        return

    face = Face(
        bbox=bbox,
        kps=keypoints,
        det_score=tracked_face['confidence'],
    )
    engine = get_face_engine()
    with inference_lock:
        engine.models['recognition'].get(image, face)
    if face.normed_embedding is None:
        return

    state.last_sample_at = timestamp
    state.samples.append(VideoSample(
        quality=quality,
        embedding=face.normed_embedding.astype(np.float32),
        face_image=state.best_image,
    ))
    state.samples.sort(key=lambda sample: sample.quality, reverse=True)
    del state.samples[APP_SETTINGS.RECOGNITION_SAMPLES:]


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
    return (
            confidence * 0.20
            + min(1.0, face_size / 180) * 0.20
            + min(1.0, sharpness / 140) * 0.30
            + max(0.0, 1.0 - abs(brightness - 132) / 100) * 0.15
            + max(0.0, 1.0 - eye_tilt / 0.14 - nose_offset / 0.22) * 0.15
    )


def _encode_face_image(image: np.ndarray, bbox: np.ndarray) -> str | None:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = bbox.astype(int)
    padding_x = max(8, int((x2 - x1) * 0.18))
    padding_y = max(8, int((y2 - y1) * 0.18))
    x1, y1 = max(0, x1 - padding_x), max(0, y1 - padding_y)
    x2, y2 = min(width, x2 + padding_x), min(height, y2 + padding_y)
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
