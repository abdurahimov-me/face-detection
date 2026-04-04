import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator, Unicode

from ..choices import BaseEnum


class EnumField(TypeDecorator):
    impl = Unicode
    cache_ok = True

    def __init__(
            self,
            enum: type(BaseEnum),
            null: bool = False,
            *args,
            **kwargs
    ):
        self.enum = enum
        self.null = null
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is None and self.null is True:
            return None

        if value not in self.enum.get_values():
            return ValueError(f"{value} not in {self.enum.get_values}")
        return value if not hasattr(value, 'value') else value.value

    def process_result_value(self, value, dialect):
        return value


class IntEnumField(EnumField):
    impl = sa.SmallInteger
    cache_ok = True


class StrEnumField(EnumField):
    impl = sa.String
    cache_ok = True
