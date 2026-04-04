import typing as t
from uuid import UUID

from pydantic import BaseModel, Field

from resources.enums import MessageType


class SendMessageModel(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    conversation_uuid: UUID
    reply_id: t.Optional[int] = None


class SendFilesModel(BaseModel):
    conversation_uuid: UUID
    reply_id: t.Optional[int] = None
    type: MessageType
    text: str = Field(min_length=1, max_length=10000)
    files: t.List[int]
