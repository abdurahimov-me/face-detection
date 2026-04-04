__all__ = (
    'OrmManager',
)

from typing import Any

import sqlalchemy as sa


class OrmManager:

    @classmethod
    def select(cls, *args, **kwargs) -> sa.Select[Any]:
        if hasattr(cls, 'deleted'):
            return sa.select(cls, *args, **kwargs).where(sa.and_(cls.deleted.is_not(True)))
        return sa.select(cls, *args, **kwargs)

    @classmethod
    def update(cls) -> sa.Update:
        return sa.update(cls)

    @classmethod
    def delete(cls) -> sa.Delete:
        return sa.delete(cls)

    @classmethod
    def insert(cls) -> sa.Insert:
        return sa.insert(cls)
