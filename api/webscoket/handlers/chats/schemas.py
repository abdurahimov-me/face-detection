import typing as t

from pydantic import BaseModel, Field

from api.shared.schemas import ConversationModel, MessageModel


class SendMessageModel(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    conversation_id: int
    reply_id: int = None


class ChatListModel(ConversationModel):
    unread: int = 5
    members: int = 2
    online: bool = False
    last_message: MessageModel


class ConversationModelResponse(BaseModel):
    data: t.List[ChatListModel]

    class Config:
        from_attributes = True
