import asyncio
import shutil
import time
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from api.detection.services import resolve_identities
from config import APP_SETTINGS
from resources.detection.data import TrackIdentity
from .processor import VideoScanResult, scan_video
from .schemas import VideoAnalysisResult, VideoInterval, VideoPerson
from .store import VideoJob, video_jobs

video_analysis_semaphore = asyncio.Semaphore(1)


@dataclass
class _PersonAggregate:
    identity_key: str
    status: t.Literal['known', 'unknown']
    user_id: str | None
    full_name: str
    best_image: str | None = None
    best_quality: float = -1.0
    scores: t.List[float] = field(default_factory=list)
    intervals: t.List[VideoInterval] = field(default_factory=list)


async def process_video_job(job_id: str, video_path: Path) -> None:
    job = video_jobs.get(job_id)
    if job is None:
        shutil.rmtree(video_path.parent, ignore_errors=True)
        return

    try:
        async with video_analysis_semaphore:
            job.status = 'processing'
            loop = asyncio.get_running_loop()

            def report_progress(progress: float) -> None:
                loop.call_soon_threadsafe(_set_progress, job, progress)

            scan = await asyncio.to_thread(scan_video, video_path, report_progress)
            eligible = [
                track
                for track in scan.tracks
                if len(track.samples) >= APP_SETTINGS.RECOGNITION_SAMPLES
            ]
            groups = [
                [sample.embedding.tolist() for sample in track.samples]
                for track in eligible
            ]
            identities = await resolve_identities(groups) if groups else []
            resolved = {
                id(track): identity
                for track, identity in zip(eligible, identities, strict=True)
            }
            job.progress = 95.0
            job.result = _build_result(job, scan, resolved)
            job.progress = 100.0
            job.status = 'completed'
            job.expires_at = (
                    time.monotonic() + APP_SETTINGS.VIDEO_RESULT_TTL_SECONDS
            )
    except asyncio.CancelledError:
        job.status = 'failed'
        job.error = 'Video tahlili bekor qilindi.'
        raise
    except Exception as exc:
        job.status = 'failed'
        job.error = str(exc) or 'Video tahlilida noma’lum xatolik.'
        job.expires_at = time.monotonic() + APP_SETTINGS.VIDEO_RESULT_TTL_SECONDS
    finally:
        shutil.rmtree(video_path.parent, ignore_errors=True)


def _set_progress(job: VideoJob, progress: float) -> None:
    if job.status == 'processing':
        job.progress = max(job.progress, min(85.0, progress))


def _build_result(
        job: VideoJob,
        scan: VideoScanResult,
        resolved: t.Dict[int, TrackIdentity],
) -> VideoAnalysisResult:
    people: t.Dict[str, _PersonAggregate] = {}
    unknown_prototypes: t.Dict[str, np.ndarray] = {}
    unknown_sequence = 0

    for track in sorted(scan.tracks, key=lambda item: item.start):
        identity = resolved.get(id(track), TrackIdentity())
        prototype = track.prototype
        if identity.user_id is not None:
            identity_key = f'user:{identity.user_id}'
            aggregate = people.setdefault(
                identity_key,
                _PersonAggregate(
                    identity_key=identity_key,
                    status='known',
                    user_id=identity.user_id,
                    full_name=identity.full_name,
                ),
            )
            if identity.score is not None:
                aggregate.scores.append(identity.score)
        else:
            identity_key = _match_unknown(prototype, unknown_prototypes)
            if identity_key is None:
                unknown_sequence += 1
                identity_key = f'unknown:{unknown_sequence}'
                if prototype is not None:
                    unknown_prototypes[identity_key] = prototype
            elif prototype is not None:
                merged = unknown_prototypes[identity_key] + prototype
                norm = float(np.linalg.norm(merged))
                if norm > 0:
                    unknown_prototypes[identity_key] = merged / norm
            aggregate = people.setdefault(
                identity_key,
                _PersonAggregate(
                    identity_key=identity_key,
                    status='unknown',
                    user_id=None,
                    full_name=f'Noma’lum #{identity_key.split(":")[-1]}',
                ),
            )

        aggregate.intervals.append(VideoInterval(
            start=round(track.start, 2),
            end=round(track.end, 2),
        ))
        if track.best_image is not None and track.best_quality > aggregate.best_quality:
            aggregate.best_quality = track.best_quality
            aggregate.best_image = track.best_image

    result_people = [
        VideoPerson(
            identity_key=person.identity_key,
            status=person.status,
            user_id=person.user_id,
            full_name=person.full_name,
            score=(
                sum(person.scores) / len(person.scores) if person.scores else None
            ),
            face_image=person.best_image,
            appearances=len(person.intervals),
            intervals=person.intervals,
        )
        for person in people.values()
    ]
    result_people.sort(key=lambda person: (person.status != 'known', person.intervals[0].start))
    return VideoAnalysisResult(
        job_id=job.job_id,
        filename=job.filename,
        duration=round(scan.duration, 2),
        analyzed_fps=round(scan.analyzed_fps, 2),
        processed_frames=scan.processed_frames,
        people=result_people,
    )


def _match_unknown(
        prototype: np.ndarray | None,
        candidates: t.Dict[str, np.ndarray],
) -> str | None:
    if prototype is None:
        return None
    best_key = None
    best_score = -1.0
    for identity_key, candidate in candidates.items():
        score = float(np.dot(prototype, candidate))
        if score > best_score:
            best_key = identity_key
            best_score = score
    if best_score < APP_SETTINGS.UNKNOWN_CLUSTER_THRESHOLD:
        return None
    return best_key
