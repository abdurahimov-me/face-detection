import typing as t
from uuid import UUID

from pydantic import BaseModel

from utils.customs import DateTime
from utils.customs.formats.aws import FileFormat


class FileModel(BaseModel):
    id: int
    file: FileFormat
    ext: str
    filename: str
    size: int
    user_id: int

    class Config:
        from_attributes = True


class MessageModel(BaseModel):
    id: int
    created_at: DateTime
    text: t.Optional[str]
    topic_id: t.Optional[int] = None
    reply_id: t.Optional[int] = None
    sender_id: int
    read: bool = False
    type: int

    class Config:
        from_attributes = True


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    name: str
    type: int

    class Config:
        from_attributes = True
