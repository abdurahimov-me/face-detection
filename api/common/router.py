from fastapi import APIRouter, Depends

from resources.depends import get_token_payload
from . import services, schemas

router = APIRouter(
    prefix='/common',
    tags=['common'],
)


@router.get('/health')
async def health():
    return {'status': 'ok'}


@router.post(
    '/upload-file',
    dependencies=[Depends(get_token_payload)]
)
async def create_file(
        service: services.CommonService.annotated("db", "payload"),
        schema: schemas.CreateFileSchema.as_form,
):
    return await service.create_file(files)


@router.put(
    '/update-file',
    dependencies=[Depends(get_token_payload)]
)
async def update_file(
        service: services.CommonService.annotated("db"),
        schema: schemas.UpdateFileSchema.as_form,
):
    return await service.update_file(schema)
