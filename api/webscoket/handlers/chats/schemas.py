import typing as t
from uuid import UUID

from pydantic import BaseModel


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    last_message: str = "Brodarim nima gap"
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
