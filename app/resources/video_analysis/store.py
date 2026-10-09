import time
import typing as t

from .data import VideoJob


class VideoJobStore:
    def __init__(self) -> None:
        self._jobs: t.Dict[str, VideoJob] = {}

    def create(self, job_id: str, filename: str) -> VideoJob:
        self.prune()
        job = VideoJob(job_id=job_id, filename=filename)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> VideoJob | None:
        self.prune()
        return self._jobs.get(job_id)

    def pop(self, job_id: str) -> VideoJob | None:
        return self._jobs.pop(job_id, None)

    def prune(self) -> None:
        now = time.monotonic()
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.expires_at is not None and job.expires_at <= now
        ]
        for job_id in expired:
            self._jobs.pop(job_id, None)


video_jobs = VideoJobStore()
