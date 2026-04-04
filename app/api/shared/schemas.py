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
    id: int = 1
    created_at: DateTime = datetime.now()
    text: str = "Brodarim nima gap"
    topic_id: t.Optional[int] = None
    reply_id: t.Optional[int] = None
    sender_id: int = 1
    read: bool = False
    conversation_id: int = 1
    type: int = 1

    class Config:
        from_attributes = True


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    name: str
    type: int

    class Config:
        from_attributes = True
