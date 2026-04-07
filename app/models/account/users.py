__all__ = (
    'User',
)

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from config.redis import cache
from utils.security import fernet
from ..base import BaseModel
from ..mixinis import DeletedMixin


class User(BaseModel, DeletedMixin):
    __tablename__ = "users"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "tenant", name="uq_user_tenant"),
    )

    first_name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=True,
    )
    last_name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=True,
    )
    middle_name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=True,
    )
    face: Mapped[str] = mapped_column(
        sa.String(1000),
        nullable=True,
    )

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        index=True,
    )
    tenant: Mapped[str] = mapped_column(
        sa.String(255),
        index=True,
    )
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict(),
    )

    @property
    def conn_id(self):
        return f"{self.user_id}:{self.tenant}"

    @property
    def encrypt(self):
        key = f"{self.user_id}:{self.tenant}"
        return fernet.encrypt(key)

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}"

    async def mark_as_typing(self):
        key = f"user_typing:{self.id}"
        await cache.set(key, True, 5)

    async def mark_as_online(self):
        key = f"user_online:{self.id}"
        await cache.set(key, True, 7)
