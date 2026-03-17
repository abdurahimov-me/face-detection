__all__ = (
    'Conversation',
)

from typing import TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

T = TypeVar("T", bound="Base")


from ..base import BaseModel
from ..mixinis import UUIDMixin, DeletedMixin


class Conversation(BaseModel, UUIDMixin, DeletedMixin):
    __tablename__ = "conversations"

    name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=True,
    )
    type: Mapped[int] = mapped_column(
        sa.SmallInteger(),
        index=True,
    )
    owner_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )


