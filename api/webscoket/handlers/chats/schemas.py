import typing as t

from pydantic import BaseModel

from api.shared.schemas import ConversationModel


class ChatListModel(ConversationModel):
    unread: int = 5
    members: int = 2
    online: bool = False


class ConversationModelResponse(BaseModel):
    data: t.List[ChatListModel]

    class Config:
        from_attributes = True
