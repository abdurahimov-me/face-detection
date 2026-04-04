__all__ = (
    'Conversation',
)

import typing as t
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from config.redis import cache
from resources.enums import ConversationType
from utils.customs import IntEnumField
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
    async def get_conversation_field(
            session: AsyncSession,
            value: t.Union[int, UUID],
            field_name: t.Literal["id", "uuid"],
    ) -> t.Optional[t.Union[int, str]]:
        key = f"conversation_{field_name}:{value}"
        if cached := await cache.get(key):
            return cached

        column = getattr(Conversation, field_name)
        result = await session.execute(
            sa.select(column)
            .where(column == value if field_name == "id" else column == value)
            .limit(1)
        )
        row = result.first()
        field_value = row[0] if row else None

        if field_value is not None:
            await cache.set(key, str(field_value), CHAT_ID_TTL)

        return field_value
