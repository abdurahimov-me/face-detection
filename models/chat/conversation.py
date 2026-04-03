__all__ = (
    'Conversation',
)

from typing import TypeVar
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from config.redis import cache
from resources.enums import ConversationType
from utils.customs import IntEnumField

T = TypeVar("T", bound="Base")

from ..base import BaseModel
from ..mixinis import UUIDMixin, DeletedMixin

CHAT_ID_TTL = 20 * 60


class Conversation(BaseModel, UUIDMixin, DeletedMixin):
    __tablename__ = "conversations"

    name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=True,
    )
    type: Mapped[int] = mapped_column(
        IntEnumField(ConversationType),
        default=ConversationType.DIRECT,
        index=True,
    )
    poster_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("files.id"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    @staticmethod
    async def get_conversation_id(
            session: AsyncSession,
            chat_uuid: UUID
    ) -> int:
        key = f"conversation_id:{chat_uuid}"
        if value := await cache.get(key):
            return value
        chat = await Conversation.repo.db_first(session=session, chat_uuid=chat_uuid)
        await cache.set(key, chat.id, CHAT_ID_TTL)
        return chat.id
