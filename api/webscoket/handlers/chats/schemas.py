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


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    last_message: MessageModel
    unread: int = 5
    members: int = 2
    name: str
    type: int
    online: bool = False

    class Config:
        from_attributes = True


class ConversationModelResponse(BaseModel):
    data: t.List[ConversationModel]

    class Config:
        from_attributes = True
