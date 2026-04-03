import typing as t
from uuid import UUID
from pydantic import BaseModel, Field

from api.shared.schemas import MessageModel


class SendMessageModel(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    conversation_uuid: UUID
    reply_id: int = None



class SendPhotosModel(BaseModel):
    conversation_uuid: UUID
    reply_id: int = None
    text: str = Field(min_length=1, max_length=10000)
    files: t.List[int]