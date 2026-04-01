__all__ = (
    'Message',
    'MessageRead'
)

import typing as t

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property

from ..base import BaseModel, Base
from ..mixinis import DeletedMixin

if t.TYPE_CHECKING:
    from .files import File


class MessageRead(Base):
    __tablename__ = "message_reads"
    id = None

    message_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    read_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
    )


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
    topic_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("topics.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    text: Mapped[str] = mapped_column(
        sa.Text(),
    )
    reply_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("messages.id", ondelete="CASCADE"),
        index=True,
    )
    read = column_property(
        sa.select(sa.literal(True))
        .where(
            sa.exists().where(
                sa.and_(
                    MessageRead.message_id == id,
                )
            )
        )
        .correlate_except(MessageRead)
        .scalar_subquery()
    )

    files: Mapped[t.List['File']] = relationship(
        "File",
        secondary="message_files",
        back_populates="messages",
        passive_deletes=True,
    )
