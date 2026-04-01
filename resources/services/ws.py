import inspect
from typing import Annotated, Sequence, Optional, Any, Callable, AsyncIterator, Iterable, Type, TypeVar

from fastapi import Depends
from fastapi import Request
from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import get_db, db_helper
from utils import Payload

T = TypeVar('T', bound='BaseService')

ARGS_TYPE = {
    'db': Annotated[AsyncSession, Depends(get_db)],
}


class BaseWSService:
    session: Callable[..., AsyncIterator[AsyncSession]] = db_helper.session

    def __init__(
            self,
            db: AsyncSession = None,
    ):
        self.db: 'AsyncSession' = db

    async def commit(self):
        return await self.db.commit()

    async def flush(self, objects: Optional[Sequence[Any]] = None):
        return await self.db.flush(objects=objects)

    async def rollback(self):
        return await self.db.rollback()

    async def close(self):
        return await self.db.close()

    def add(self, obj: Any):
        return self.db.add(obj)

    def add_all(self, instances: Iterable[object]):
        return self.db.add_all(instances)

    async def merge(self, obj: Any):
        return await self.db.merge(obj)

    async def execute(self, stmt, *args, **kwargs) -> Result[Any]:
        if self.db is not None:
            return await self.db.execute(stmt, *args, **kwargs)
        else:
            async with self.session() as db:
                result = await db.execute(stmt, *args, **kwargs)
            return result

    async def refresh(self, obj: Any, attribute_names=None, with_for_update=None):
        return await self.db.refresh(obj, attribute_names, with_for_update)

    @classmethod
    def __get_parameters(cls, fields):
        parameters = []
        for field in fields:
            parameters.append(
                inspect.Parameter(
                    field,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=ARGS_TYPE[field]
                )
            )
        return parameters

    @classmethod
    def create_service(cls, *fields: str):

        parameters = cls.__get_parameters(fields or tuple())

        async def dynamic_method(**kwargs):
            return cls(**kwargs)

        sig = inspect.signature(dynamic_method)
        sig = sig.replace(parameters=parameters)
        dynamic_method.__signature__ = sig

        return dynamic_method

    @classmethod
    def annotated(cls: Type[T], *fields: str) -> type[Annotated[T, Depends]]:
        return Annotated[cls, Depends(cls.create_service(*fields))]
