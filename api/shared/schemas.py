import typing as t
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class MessageModel(BaseModel):
    id: int = 1
    created_at: datetime = datetime.now()
    text: str = "Brodarim nima gap"
    topic_id: t.Optional[int] = None
    reply_id: t.Optional[int] = None
    sender_id: int = 1
    read: bool = False
    conversation_id: int = 1


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    name: str
    type: int

    class Config:
        from_attributes = True
