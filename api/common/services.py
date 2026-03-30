from models import File
from resources.enums import FileType
from resources.services import BaseService


class CommonService(BaseService):

    async def upload_file(
            self,
            file: File,
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
