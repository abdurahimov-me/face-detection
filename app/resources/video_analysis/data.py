import math
import typing as t
from dataclasses import dataclass, field

import numpy as np

from api.video_analysis.schemas import VideoAnalysisResult, VideoJobState, VideoJobStatus, VideoInterval


@dataclass
class VideoSample:
    quality: float
    embedding: np.ndarray
    face_image: str | None


@dataclass
class VideoTrackResult:
    track_id: int
    start: float
    end: float
    samples: t.List[VideoSample]
    best_image: str | None
    best_quality: float

    @property
    def prototype(self) -> np.ndarray | None:
        if not self.samples:
            return None
        vector = np.mean([sample.embedding for sample in self.samples], axis=0)
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm > 0 else None


@dataclass
class ActiveTrack:
    track_id: int
    start: float
    end: float
    last_seen_step: int
    last_sample_at: float = -math.inf
    samples: t.List[VideoSample] = field(default_factory=list)
    best_image: str | None = None
    best_quality: float = -1.0

    def finish(self) -> VideoTrackResult:
        return VideoTrackResult(
            track_id=self.track_id,
            start=self.start,
            end=self.end,
            samples=self.samples,
            best_image=self.best_image,
            best_quality=self.best_quality,
        )


@dataclass
class PersonAggregate:
    identity_key: str
    status: t.Literal['known', 'unknown']
    user_id: str | None
    full_name: str
    best_image: str | None = None
    best_quality: float = -1.0
    scores: t.List[float] = field(default_factory=list)
    intervals: t.List[VideoInterval] = field(default_factory=list)


@dataclass
class VideoScanResult:
    duration: float
    analyzed_fps: float
    processed_frames: int
    tracks: t.List[VideoTrackResult]


@dataclass
class VideoJob:
    job_id: str
    filename: str
    status: VideoJobStatus = 'queued'
    progress: float = 0.0
    error: str | None = None
    result: VideoAnalysisResult | None = None
    expires_at: float | None = None

    def public_state(self) -> VideoJobState:
        return VideoJobState(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            filename=self.filename,
            error=self.error,
        )
