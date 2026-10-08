import typing as t

from fastapi import HTTPException
from pydantic import GetJsonSchemaHandler
from pydantic_core import CoreSchema

from utils.customs.formats import BaseFormat


class BaseValidator(BaseFormat):
    functions: t.Iterable[t.Callable] = ...
    example: str = ...
    checker: t.Callable = all
    json_schema: t.Dict[str, t.Any] = {"type": "str", "format": "str", "description": "String"}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        if not (cls.example and cls.functions):
            raise ValueError(f'Must be example and validation functions')

    @classmethod
    def validator(cls, value: t.Any):
        checking = cls.checker([func(value) for func in cls.functions])

        if not checking:
            raise HTTPException(
                status_code=422,
                detail=f"Validation failed {cls.__name__}. Example: {cls.example}",
            )

    @classmethod
    def __get_pydantic_json_schema__(
            cls, _core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> t.Dict[str, t.Any]:
        return cls.json_schema

    @classmethod
    def validate(cls, v=None, *args, **kwargs):
        cls.validator(value=v)
        return v
