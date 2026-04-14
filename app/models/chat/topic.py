__all__ = (
    'Topic',
)

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from ..base import BaseModel
from ..mixinis import DeletedMixin


class Topic(BaseModel, DeletedMixin):
    __tablename__ = "topics"

    executor_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(
        sa.String(255),
    )
    background: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=True,
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict(),
    )

