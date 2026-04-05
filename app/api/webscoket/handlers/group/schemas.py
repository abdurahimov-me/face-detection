import typing as t
from uuid import UUID

from pydantic import BaseModel

from utils.customs.formats.fernet import FernetEncrypt


class CreateGroup(BaseModel):
    name: str
    users: t.List[FernetEncrypt]


class AddUsersToGroup(BaseModel):
    conversation_uuid: UUID
    users: t.List[FernetEncrypt]
