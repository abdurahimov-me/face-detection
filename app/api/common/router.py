import typing as t

from fastapi import APIRouter, Depends

from integrations.grpc.services import user_service
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


@router.put(
    '/update-file/',
    dependencies=[Depends(get_token_payload)]
)
async def update_file(
        service: services.CommonService.annotated("db"),
        schema: schemas.UpdateFileSchema.as_form,
):
    return await service.update_file(schema)


@router.get(
    "/testtt"
)
async def testtt():
    return {
        "user": user_service.get_user(122131, "salom"),
        "users": user_service.get_users([12312, 12312], "salom"),
    }
