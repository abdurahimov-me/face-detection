import typing as t

from pydantic import BaseModel

from api.shared.schemas import ConversationModel, MessageModel


class ChatListModel(ConversationModel):
    unread: int = 5
    members: int = 2
    online: bool = False
    last_message: MessageModel


class ConversationModelResponse(BaseModel):
    data: t.List[ChatListModel]

    class Config:
        from_attributes = True
