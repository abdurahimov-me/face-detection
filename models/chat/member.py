__all__ = (
    'Member',
)

from datetime import datetime
from typing import TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from utils import utcnow

T = TypeVar("T", bound="Base")

from ..base import BaseModel
from ..mixinis import DeletedMixin


class Member(BaseModel, DeletedMixin):
    __tablename__ = "members"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[int] = mapped_column(
        sa.SmallInteger(),
    )
    joined_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utcnow,
    )
    left_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
