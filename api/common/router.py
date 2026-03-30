from fastapi import APIRouter, UploadFile, File
from . import services, schemas


router = APIRouter(
    prefix='/common'
)


@router.get('/health')
async def health():
    return {'status': 'ok'}


@router.get('/upload-file')
async def upload_file(
        file: UploadFile = File(...)
):
    pass
