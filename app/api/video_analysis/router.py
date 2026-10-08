import shutil
import tempfile
import typing as t
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status

from config import APP_SETTINGS
from .schemas import VideoAnalysisResult, VideoJobAccepted, VideoJobState
from .services import process_video_job
from .store import video_jobs


router = APIRouter(prefix='/video-analysis', tags=['Video analysis'])
VIDEO_SUFFIXES = {'.mp4', '.mov', '.avi', '.webm', '.mkv'}


@router.post('', response_model=VideoJobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_video_analysis(
    background_tasks: BackgroundTasks,
    file: t.Annotated[UploadFile, File()],
) -> VideoJobAccepted:
    filename = Path(file.filename or 'video').name
    suffix = Path(filename).suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise HTTPException(status_code=415, detail='Video formati qo‘llab-quvvatlanmaydi.')
    if file.content_type and file.content_type not in APP_SETTINGS.ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=415, detail='Video MIME turi noto‘g‘ri.')

    job_id = str(uuid4())
    directory = Path(tempfile.gettempdir()) / 'face-video-analysis' / job_id
    directory.mkdir(parents=True, exist_ok=False)
    uploading_path = directory / 'input.uploading'
    video_path = directory / f'input{suffix}'
    size = 0
    try:
        async with aiofiles.open(uploading_path, 'wb') as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > APP_SETTINGS.MAX_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail='Video hajmi juda katta.')
                await output.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail='Bo‘sh video yuborildi.')
        uploading_path.replace(video_path)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finally:
        await file.close()

    video_jobs.create(job_id, filename)
    background_tasks.add_task(process_video_job, job_id, video_path)
    return VideoJobAccepted(job_id=job_id, status='queued')


@router.get('/{job_id}', response_model=VideoJobState)
async def get_video_analysis(job_id: str) -> VideoJobState:
    job = video_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Video tahlili topilmadi.')
    return job.public_state()


@router.get('/{job_id}/result', response_model=VideoAnalysisResult)
async def get_video_analysis_result(job_id: str) -> VideoAnalysisResult:
    job = video_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Video tahlili topilmadi.')
    if job.status == 'failed':
        video_jobs.pop(job_id)
        raise HTTPException(status_code=422, detail=job.error or 'Video tahlili bajarilmadi.')
    if job.status != 'completed' or job.result is None:
        raise HTTPException(status_code=409, detail='Video tahlili hali tugamagan.')
    result = job.result
    video_jobs.pop(job_id)
    return result
