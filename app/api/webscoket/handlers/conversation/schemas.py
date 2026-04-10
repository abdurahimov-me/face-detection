import typing as t
from uuid import UUID

from pydantic import BaseModel, Field

from api.shared.schemas import MessageModel, FileModel
from utils.customs import DateTime
from utils.customs.formats.file import HrCoreFileFormat


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
    first_name: t.Optional[str]
    last_name: t.Optional[str]
    face: HrCoreFileFormat
    reply_first_name: t.Optional[str] = None
    reply_last_name: t.Optional[str] = None
    reply_text: t.Optional[str] = None
    reply_type: t.Optional[int] = None
    files: t.Optional[t.List[FileModel]] = None


class ResponseMessageModel(BaseModel):
    prev_cursor: t.Optional[int] = None
    next_cursor: t.Optional[int] = None
    unread_count: int = 0
    messages: t.List[ChatMessageModel]


class GetReadUsersModel(BaseModel):
    conversation_uuid: UUID
    message_id: int


class ReadUserModelResponse(BaseModel):
    id: int
    first_name: t.Optional[str]
    last_name: t.Optional[str]
    face: HrCoreFileFormat
    read_at: DateTime


class ReadUsersModelResponse(BaseModel):
    users: t.List[ReadUserModelResponse]


class ConversationInfoModel(BaseModel):
    conversation_uuid: UUID