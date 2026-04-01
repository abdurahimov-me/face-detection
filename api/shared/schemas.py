import typing as t
from uuid import UUID

from pydantic import BaseModel


class MessageModel(BaseModel):
    id: int = 1
    time: str = "12:00"
    text: str = "Brodarim nima gap"
    topic_id: int = None
    reply_id: int = None
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
