import typing as t
from uuid import UUID

from pydantic import BaseModel, model_validator

from utils.customs import DateTime
from utils.customs.formats.fernet import FernetEncrypt
from utils.customs.formats.file import HrCoreFileFormat
from utils.security import fernet


class CreateGroup(BaseModel):
    name: str
    poster_id: t.Optional[int] = None
    users: t.List[FernetEncrypt]


class EditGroup(BaseModel):
    name: t.Optional[str] = None
    poster_id: t.Optional[int] = None
    users: t.List[FernetEncrypt] = []


class AddUsersToGroup(BaseModel):
    conversation_uuid: UUID
    users: t.List[FernetEncrypt]


class GetUsersFromGroup(BaseModel):
    conversation_uuid: UUID


class MembersModel(BaseModel):
    id: int
    user_id: int
    first_name: t.Optional[str]
    last_name: t.Optional[str]
    role: int
    face: HrCoreFileFormat
    joined_at: DateTime
    encrypt: t.Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def generate_encrypt(cls, data):
        data = dict(data)
        if data.get("encrypt"):
            return data

        user_id = data.get("user_id")
        tenant = data.get("tenant")

        if user_id and tenant:
            key = f"{user_id}:{tenant}"
            data = dict(data)
            data["encrypt"] = fernet.encrypt(key)

        return data

    class Config:
        from_attributes = True


class GetUsersFromGroupResponse(BaseModel):
    members: t.List[MembersModel]
