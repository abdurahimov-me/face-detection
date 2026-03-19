__all__ = (
    'Message',
)

import typing as t

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel, Base
from ..mixinis import DeletedMixin

if t.TYPE_CHECKING:
    from .files import File, SecondaryFile


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

    files: Mapped[t.List['File']] = relationship(
        "File",
        secondary="message_files",
        back_populates="messages",
        passive_deletes=True,
    )
