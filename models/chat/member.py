__all__ = (
    'Member',
)

from datetime import datetime
from typing import TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from resources.enums import MemberType
from utils import utcnow
from utils.customs import IntEnumField

T = TypeVar("T", bound="Base")

from ..base import BaseModel
from ..mixinis import DeletedMixin


class Member(BaseModel, DeletedMixin):
    __tablename__ = "members"
    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", 'conversation_id', name='user_conversation_id'
        )
    )

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
        IntEnumField(MemberType),
        default=MemberType.MEMBER,
    )
    joined_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utcnow,
    )
    left_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
