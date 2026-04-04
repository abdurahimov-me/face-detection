import typing as t

from pydantic import BaseModel

from utils.customs.formats.fernet import FernetEncrypt


class CreateGroup(BaseModel):
    name: str
    users: t.List[FernetEncrypt]
