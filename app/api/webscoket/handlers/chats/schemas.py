import typing as t

from pydantic import BaseModel

from api.shared.schemas import ConversationModel, MessageModel


class ChatListModel(ConversationModel):
    unread: int = 5
    members: int = 2
    online: bool = False
    unread_message_id: t.Optional[int] = None
    last_message: MessageModel


class ConversationModelResponse(BaseModel):
    command: str
    request_id: t.Any = None,
    data: t.List[ChatListModel]

    class Config:
        from_attributes = True
