from pydantic import BaseModel, Field
from api.shared.schemas import MessageModel
import typing as t


class SendMessageModel(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    conversation_id: int
    reply_id: int = None



class GetMessagesModel(BaseModel):
    conversation_id: int
    cursor: int = None



class ResponseMessageModel(BaseModel):
    next_cursor: t.Optional[int] = None
    messages: t.List[MessageModel]

