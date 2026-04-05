import typing as t
from uuid import UUID

from pydantic import BaseModel

from utils.customs import DateTime
from utils.customs.formats.aws import AWSFormat
from utils.customs.formats.fernet import FernetEncrypt


class CreateGroup(BaseModel):
    name: str
    poster_id:t.Optional [int] = None
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
    face: AWSFormat
    joined_at: DateTime

    class Config:
        from_attributes = True


class GetUsersFromGroupResponse(BaseModel):
    members: t.List[MembersModel]
