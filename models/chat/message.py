__all__ = (
    'Member',
)

from typing import TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

T = TypeVar("T", bound="Base")

from ..base import BaseModel
from ..mixinis import DeletedMixin


class Message(BaseModel, DeletedMixin):
    __tablename__ = "messages"

    sender_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    text: Mapped[str] = mapped_column(
        sa.Text(),
    )
    reply_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("messages.id", ondelete="CASCADE"),
        index=True,
    )


class MessageFile(BaseModel, DeletedMixin):
    __tablename__ = "message_files"

    message_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("messages.id", ondelete="CASCADE"),
        index=True,
    )
    file: Mapped[str] = mapped_column(
        sa.String(255),
    )
    type: Mapped[int] = mapped_column(
        sa.SmallInteger(),
    )
