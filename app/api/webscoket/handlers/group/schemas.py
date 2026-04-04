from pydantic import BaseModel
import typing as t
from utils.customs.formats.fernet import FernetEncrypt

class CreateGroup(BaseModel):
    name: str
    users: t.List[FernetEncrypt]