import typing as t
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from utils.customs import DateTime
from utils.customs.formats.aws import AWSFormat


class FileModel(BaseModel):
    id: int
    file: AWSFormat
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
    topic_id: t.Optional[int]
    reply_id: t.Optional[int]
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
