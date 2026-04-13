import io
import os
import typing as t
from uuid import uuid4

from PIL import Image

from models import File
from resources.enums import FileType
from resources.services import BaseHTTPService
from utils.storages import storage
from .schemas import UpdateFileSchema, CreateFileSchema, UploadAudioSchema

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


def extract_metadata(file_bytes: bytes, ext: str) -> dict:
    metadata = {}

    metadata["size"] = len(file_bytes)

    if ext in ALLOWED_PHOTO_EXTS:
        try:
            img = Image.open(io.BytesIO(file_bytes))
            metadata["width"] = img.width
            metadata["height"] = img.height
            metadata["format"] = img.format
        except Exception:
            pass

    return metadata


class CommonService(BaseHTTPService):

    async def create_file(
            self,
            schema: CreateFileSchema,
    ) -> t.List[File]:
        user = await self.get_user(rais_exception=True)
        objects = []

        for file in schema.files:
            _, ext = os.path.splitext(file.filename)
            ext = ext.lower()

            unique_filename = f"{uuid4()}{ext}"
            file_type = get_file_type(ext)
            file_path = f"files/{unique_filename}"

            file_bytes = await file.read()

            metadata = extract_metadata(file_bytes, ext)

            content = io.BytesIO(file_bytes)
            await storage.async_upload_fileobj(content, file_path)

            db_file = File(
                file=file_path,
                ext=ext.lstrip("."),
                filename=file.filename,
                size=metadata.get("size"),
                type=file_type,
                user_id=user.id,
                meta_data=metadata,
            )

            objects.append(db_file)

        self.add_all(objects)
        await self.commit()
        return objects

    async def upload_audio(
            self,
            schema: UploadAudioSchema,
    ) -> File:
        user = await self.get_user(rais_exception=True)

        _, ext = os.path.splitext(schema.file.filename)
        ext = ext.lower()

        unique_filename = f"{uuid4()}{ext}"
        file_type = get_file_type(ext)
        file_path = f"files/{unique_filename}"

        file_bytes = await schema.file.read()
        metadata = schema.metadata or {}
        extra_metadata = extract_metadata(file_bytes, ext)
        metadata = {**metadata, **extra_metadata}

        content = io.BytesIO(file_bytes)
        await storage.async_upload_fileobj(content, file_path)

        db_file = File(
            file=file_path,
            ext=ext.lstrip("."),
            filename=schema.file.filename,
            size=metadata.get("size"),
            type=file_type,
            user_id=user.id,
            meta_data=metadata,
        )

        self.add(db_file)
        await self.commit()
        return db_file

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
        file_path = f"files/{unique_filename}"

        file_bytes = await schema.file.read()

        metadata = extract_metadata(file_bytes, ext)

        content = io.BytesIO(file_bytes)
        await storage.async_upload_fileobj(content, file_path)

        # update db
        db_file.file = file_path
        db_file.ext = ext.lstrip(".")
        db_file.filename = schema.file.filename
        db_file.size = metadata.get("size")
        db_file.type = file_type
        db_file.meta_data = metadata

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
