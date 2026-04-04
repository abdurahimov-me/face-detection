import typing as t
from uuid import UUID
from pydantic import BaseModel, Field

from api.shared.schemas import MessageModel, FileModel


class SendMessageModel(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    conversation_id: int
    reply_id: int = None


class GetMessagesModel(BaseModel):
    conversation_uuid: UUID
    cursor: t.Optional[int] = None
    direction: t.Optional[str] = None



class MarkAsReadModel(BaseModel):
    message_id: int
    conversation_uuid: UUID


class ChatMessageModel(MessageModel):
    user_id: int
    files: t.Optional[t.List[FileModel]] = None


class ResponseMessageModel(BaseModel):
    prev_cursor: t.Optional[int] = None
    next_cursor: t.Optional[int] = None
    unread_count: int = 0
    messages: t.List[ChatMessageModel]
