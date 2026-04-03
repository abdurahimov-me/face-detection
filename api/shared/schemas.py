import typing as t
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BaseWSResponse(BaseModel):
    success: bool = False
    request_id: t.Any = None
    command: str
    data: t.Any = None


class MessageModel(BaseModel):
    id: int = 1
    created_at: datetime = datetime.now()
    text: str = "Brodarim nima gap"
    topic_id: t.Optional[int] = None
    reply_id: t.Optional[int] = None
    sender_id: int = 1
    read: bool = False
    conversation_id: int = 1
    type: int = 1


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    name: str
    type: int

    class Config:
        from_attributes = True
