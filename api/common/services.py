from models import File
from fastapi import UploadFile
from resources.enums import FileType
from resources.services import BaseHTTPService
from .schemas import UpdateFileSchema

class CommonService(BaseHTTPService):

    async def create_file(
            self,
            file: UploadFile,
    ):
        file = File(
            file="",
            ext="docx",
            filename="dsaasdasd",
            size=21341212,
            type=FileType.PHOTO
        )
        self.add(file)
        await self.commit()
        return file

    async def update_file(
            self,
            schema: UpdateFileSchema
    ):
        file = await File.repo.db_get(id=schema.file_id)

        return file
