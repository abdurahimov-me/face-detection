import logging
import threading

import numpy as np
import supervision as sv
from insightface.app.common import Face
from trackers import ByteTrackTracker
from ..engine import get_face_engine

logger = logging.getLogger(__name__)
_inference_lock = threading.Lock()

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
        self.lock = threading.Lock()
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
