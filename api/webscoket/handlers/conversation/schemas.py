import typing as t

from pydantic import BaseModel, Field

from api.shared.schemas import MessageModel


class SendMessageModel(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    conversation_id: int
    reply_id: int = None

class GetMessagesModel(BaseModel):
    conversation_id: int
    cursor: int = None
    direction: str = "up"

class ResponseMessageModel(BaseModel):
    prev_cursor: t.Optional[int] = None
    next_cursor: t.Optional[int] = None
    unread_count: int = 0
    messages: t.List[MessageModel]