__all__ = (
    "Log",
)
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class Log(BaseModel):
    __tablename__ = 'logs'
    updated_at = None
    model: Mapped[int] = mapped_column(
        sa.SmallInteger(),
        index=True,
    )
    instance_id: Mapped[str] = mapped_column(
        sa.String(255),
        index=True,
    )
    executor: Mapped[str] = mapped_column(
        sa.String(255),
    )
    before: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict(),
    )
    after: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict(),
    )
