from fastapi import APIRouter, UploadFile, File

from . import services, schemas

router = APIRouter(
    prefix='/common',
    tags=['common'],
)


@router.get('/health')
async def health():
    return {'status': 'ok'}


@router.post('/upload-file')
async def create_file(
        service: services.CommonService.annotated("db"),
        file: UploadFile = File(...),
):
    return await service.create_file(file)


@router.put('/update-file')
async def update_file(
        service: services.CommonService.annotated("db"),
        schema: schemas.UpdateFileSchema.as_form,
):
    return await service.update_file(schema)
