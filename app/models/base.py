__all__ = (
    'BaseModel',
    'Base',
)

from typing import TypeVar, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr

from config.db import OrmManager, SqlAlchemyRepository
from utils import utcnow

T = TypeVar("T", bound="Base")


class Base(DeclarativeBase, AsyncAttrs, OrmManager):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return str(cls.__name__) + 's'

    id: Mapped[int] = mapped_column(
        sa.BigInteger(),
        primary_key=True,
        autoincrement=True,
        index=True,
        server_default=sa.Identity(
            always=False,
            start=1,
            increment=1,
            minvalue=1,
            maxvalue=9223372036854775807,
            cycle=False,
            cache=1,
        ),
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.__name__ not in ("Base", "BaseModel"):
            cls.repo = cls.get_new_repo()()

    @classmethod
    def get_new_repo(cls):
        class NewRepo(SqlAlchemyRepository):
            model = cls

        return NewRepo

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.id}>'


class BaseModel(Base):
    __abstract__ = True

    created_at: Mapped[Optional[sa.DateTime]] = mapped_column(
        sa.DateTime(timezone=True),
        default=utcnow,
        nullable=False
    )
    updated_at: Mapped[Optional[sa.DateTime]] = mapped_column(
        sa.DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
