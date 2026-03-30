from fastapi import APIRouter, UploadFile, File

from . import services, schemas

router = APIRouter(
    prefix='/common'
)


@router.get('/health')
async def health():
    return {'status': 'ok'}


@router.post('/upload-file')
async def upload_file(
        service: services.CommonService.annotated("db"),
        file: UploadFile = File(...),
):
    pass


@router.put('/update-file')
async def update_file(
        service: services.CommonService.annotated("db"),
        schema: schemas.UpdateFileSchema.as_form,
):
    pass
