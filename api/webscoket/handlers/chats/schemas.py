import typing as t
from uuid import UUID

from pydantic import BaseModel


class ConversationModel(BaseModel):
    id: int
    uuid: UUID
    name: str
    type: int

    class Config:
        from_attributes = True


class ConversationModelResponse(BaseModel):
    data: t.List[ConversationModel]

    class Config:
        from_attributes = True
