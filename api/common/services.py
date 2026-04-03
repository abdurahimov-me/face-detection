import io
import os
import typing as t
from uuid import uuid4

import aiofiles
from fastapi import UploadFile

from models import File
from resources.enums import FileType
from resources.services import BaseHTTPService
from utils.storages import storage
from .schemas import UpdateFileSchema

UPLOAD_DIR = "media"
ALLOWED_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}
ALLOWED_DOCUMENT_EXTS = {".pdf", ".docx", ".xlsx", ".txt", ".zip"}


def get_file_type(ext: str) -> FileType:
    ext = ext.lower()
    if ext in ALLOWED_PHOTO_EXTS:
        return FileType.PHOTO
    elif ext in ALLOWED_VIDEO_EXTS:
        return FileType.VIDEO
    return FileType.DOCUMENT


class CommonService(BaseHTTPService):

    async def create_file(
            self,
            files: t.List[UploadFile],
    ) -> t.List[File]:
        user = await self.get_user(rais_exception=True)
        objects = []
        for file in files:
            _, ext = os.path.splitext(file.filename)
            ext = ext.lower()
            unique_filename = f"{uuid4()}{ext}"
            file_type = get_file_type(ext)
            file_path = f"files/{unique_filename}"

            content = io.BytesIO(await file.read())
            await storage.async_upload_fileobj(content, file_path)

            db_file = File(
                file=file_path,
                ext=ext.lstrip("."),
                filename=file.filename,
                size=file.size,
                type=file_type,
                user_id=user.id,
            )
            objects.append(db_file)

        self.add_all(objects)
        await self.commit()
        return objects

    async def update_file(
            self,
            schema: UpdateFileSchema,
            user_id: int,
    ) -> File:
        db_file = await File.repo.db_get(self.db, id=schema.file_id, user_id=user_id)

        if db_file is None:
            raise ValueError("File not found")

        if os.path.exists(db_file.file):
            os.remove(db_file.file)

        _, ext = os.path.splitext(schema.file.filename)
        ext = ext.lower()
        unique_filename = f"{uuid4()}{ext}"
        file_type = get_file_type(ext)

        save_dir = os.path.join(UPLOAD_DIR, file_type.name.lower())
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, unique_filename)

        content = await schema.file.read()
        async with aiofiles.open(save_path, "wb") as f:
            await f.write(content)

        db_file.file = save_path
        db_file.ext = ext.lstrip(".")
        db_file.filename = schema.file.filename
        db_file.size = len(content)
        db_file.type = file_type

        await self.commit()
        return db_file

    async def delete_file(
            self,
            file_id: int,
            user_id: int,
    ) -> None:
        file = await File.repo.db_get(self.db, id=file_id, user_id=user_id)

        if file is None:
            raise ValueError("File not found")

        if os.path.exists(file.file):
            os.remove(file.file)

        file.deleted = True
        await self.commit()
