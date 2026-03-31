import inspect
from typing import Annotated, Sequence, Optional, Any, Callable, AsyncIterator, Iterable, Type, TypeVar

from fastapi import HTTPException, status, Depends
from fastapi import Request
from sqlalchemy import Result
from sqlalchemy.ext.asyncio import AsyncSession

from config.db import get_db, db_helper
from utils import Payload
from .decorators import permission
from ..depends.current_payload import get_token_payload_or_none

T = TypeVar('T', bound='BaseService')

ARGS_TYPE = {
    'db': Annotated[AsyncSession, Depends(get_db)],
    'payload': Annotated[Payload, Depends(get_token_payload_or_none)],
}


class BaseHTTPService:
    default_permission: Callable = None
    router_functions: Iterable[str] = None

    session: Callable[..., AsyncIterator[AsyncSession]] = db_helper.session

    def __init__(
            self,
            request: Request,
            db: AsyncSession = None,
            payload: Payload = None,
    ):
        self.request: Request = request
        self.db: 'AsyncSession' = db
        self.payload: 'Payload' = payload

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.router_functions and cls.default_permission:
            for func_name in cls.router_functions:
                if hasattr(cls, func_name):
                    original_method = getattr(cls, func_name)

                    if not getattr(original_method, "__wrapped__", None):
                        decorated_method = permission(cls.default_permission)(original_method)
                        setattr(cls, func_name, decorated_method)

    def error(self, text):
        raise HTTPException(detail=text, status_code=status.HTTP_400_BAD_REQUEST)

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

    async def get_object[T](self, stmt) -> T:
        result = await self.execute(stmt)

        if obj := result.scalar_one_or_none():
            return obj

        self.error(f"{stmt.__name__} object does not exist")

    @classmethod
    def __get_parameters(cls, fields):
        parameters = [
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Request
            )
        ]
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

        assert all(map(lambda field: field in ARGS_TYPE, fields)), 'The fields must be belong to the ARGS_TYPE'
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
