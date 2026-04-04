__all__ = (
    'DeletedMixin',
    'UUIDMixin',
)

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, declared_attr


class DeletedMixin:

    @declared_attr
    def deleted(cls) -> Mapped[str]:
        return mapped_column(sa.Boolean, default=False, index=True)


class UUIDMixin:
    @declared_attr
    def uuid(cls) -> Mapped[sa.UUID]:
        return mapped_column(sa.UUID, unique=True, index=True, server_default=sa.text("gen_random_uuid()"))
