import typing as t
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from utils.customs import DateTime
from utils.customs.formats.fernet import FernetEncrypt
from utils.customs.formats.file import HrCoreFileFormat
from utils.security import fernet


class CreateGroup(BaseModel):
    name: str
    poster_id: t.Optional[int] = None
    users: t.List[FernetEncrypt]


class AddUsersToGroup(BaseModel):
    conversation_uuid: UUID
    users: t.List[FernetEncrypt]


class GetUsersFromGroup(BaseModel):
    conversation_uuid: UUID


class MembersModel(BaseModel):
    id: int
    first_name: t.Optional[str]
    last_name: t.Optional[str]
    role: int
    face: HrCoreFileFormat
    joined_at: DateTime
    encrypt: t.Optional[str] = None

    @model_validator(mode="after")
    def set_encrypt(self):
        if not self.encrypt:
            key = f"{self.user_id}:{self.tenant}"
            self.encrypt = fernet.encrypt(key)
        return self

    class Config:
        from_attributes = True


class GetUsersFromGroupResponse(BaseModel):
    members: t.List[MembersModel]
