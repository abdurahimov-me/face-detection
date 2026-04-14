import typing as t

from fastapi import APIRouter, Depends

from resources.depends import get_token_payload
from . import services, schemas
from ..shared.schemas import FileModel

router = APIRouter(
    prefix='/common',
    tags=['common'],
)


@router.get('/health')
async def health():
    return {'status': 'ok'}


@router.post(
    '/upload-file/',
    dependencies=[Depends(get_token_payload)],
    response_model=t.List[FileModel]
)
async def create_file(
        service: services.CommonService.annotated("db", "payload"),
        schema: schemas.CreateFileSchema.as_form,
):
    return await service.create_file(schema)


@router.post(
    '/upload-audio/',
    dependencies=[Depends(get_token_payload)],
    response_model=FileModel,
)
async def create_file(
        service: services.CommonService.annotated("db", "payload"),
        schema: schemas.UploadAudioSchema.as_form,
):
    return await service.upload_audio(schema)


@router.put(
    '/update-file/',
    dependencies=[Depends(get_token_payload)]
)
async def update_file(
        service: services.CommonService.annotated("db"),
        schema: schemas.UpdateFileSchema.as_form,
):
    return await service.update_file(schema)


@router.post("/test")
async def salom(
        schema: schemas.CreateSalomSchema,
):
    return schema


@router.get("/test/{message_id}")
async def salom(
        message_id: int,
        service: services.CommonService.annotated("db"),
):
    return await service.get_read_users(message_id)
