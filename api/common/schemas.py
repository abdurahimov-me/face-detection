import typing as t

from fastapi import UploadFile
from pydantic import BaseModel

from resources.enums import FileType
from utils.customs import as_form


@as_form
class UpdateFileSchema(BaseModel):
    file_id: int
    file: UploadFile


@as_form
class CreateFileSchema(BaseModel):
    type: FileType
    files: t.List[UploadFile]
