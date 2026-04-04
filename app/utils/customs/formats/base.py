from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import CoreSchema, core_schema


class BaseFormat(ABC):
    json_schema = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        if cls.json_schema is None:
            raise ValueError("'json_schema' must be defined")

    @classmethod
    def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(
            cls, _core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> Dict[str, Any]:
        return cls.json_schema

    @classmethod
    @abstractmethod
    def validate(cls, v=None, *args, **kwargs):
        raise NotImplementedError
