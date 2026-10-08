import typing as t

from pydantic import BaseModel, Field


VideoJobStatus = t.Literal['queued', 'processing', 'completed', 'failed']


class VideoJobAccepted(BaseModel):
    job_id: str
    status: VideoJobStatus


class VideoJobState(BaseModel):
    job_id: str
    status: VideoJobStatus
    progress: float = Field(ge=0, le=100)
    filename: str
    error: str | None = None


class VideoInterval(BaseModel):
    start: float
    end: float


class VideoPerson(BaseModel):
    identity_key: str
    status: t.Literal['known', 'unknown']
    user_id: str | None = None
    full_name: str
    score: float | None = None
    face_image: str | None = None
    appearances: int
    intervals: t.List[VideoInterval]


class VideoAnalysisResult(BaseModel):
    job_id: str
    filename: str
    duration: float
    analyzed_fps: float
    processed_frames: int
    people: t.List[VideoPerson]
