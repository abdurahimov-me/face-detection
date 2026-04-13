import json
import typing as t

from fastapi import UploadFile
from pydantic import BaseModel, field_validator

from resources.enums import FileType
from utils.customs import as_form
from utils.customs.formats.fernet import UserEncrypt


@as_form
class UpdateFileSchema(BaseModel):
    file_id: int
    file: UploadFile


@as_form
class CreateFileSchema(BaseModel):
    type: FileType
    files: t.List[UploadFile]


@as_form
class UploadAudioSchema(BaseModel):
    file: UploadFile
    meta_data: t.Union[str, t.Dict[str, t.Any]]

    @field_validator('metadata', mode="after")
    def validate_metadata(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class CreateSalomSchema(BaseModel):
    partner: UserEncrypt
