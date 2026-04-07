__all__ = (
    'Message',
    'MessageRead'
)

import typing as t

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property

from resources.enums import MessageType
from utils.customs import IntEnumField
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
        index=True,
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
    type = mapped_column(
        IntEnumField(MessageType),
        server_default=sa.text("1"),
        default=MessageType.TEXT,
        index=True,
    )
    text: Mapped[str] = mapped_column(
        sa.Text(),
    )
    reply_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("messages.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict(),
    )

    files: Mapped[t.List['File']] = relationship(
        "File",
        secondary="message_files",
        back_populates="messages",
        passive_deletes=True,
    )

    def as_dict(self):
        return {
            "message_id": self.id,
            "text": self.text,
            "type": self.type,
            "reply_id": self.reply_id,
            "topic_id": self.topic_id,
            "sender_id": self.sender_id
        }


Message.read = column_property(
    sa.exists().where(
        sa.and_(
            MessageRead.message_id == Message.id,
        )
    )
)
