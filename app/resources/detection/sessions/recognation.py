import logging
import numpy as np
import supervision as sv
from insightface.app.common import Face
from trackers import ByteTrackTracker

from ..data import TrackIdentity
from ..engine import get_face_engine, inference_lock

logger = logging.getLogger(__name__)


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
        self.embedded_tracks: set[int] = set()

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
