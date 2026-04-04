from enum import Enum
from typing import Literal


class BaseEnum(Enum):

    def __repr__(self):
        return str(self.value)

    def __str__(self):
        return str(self.value)

    @classmethod
    def get_values(cls):
        return tuple(cls._value2member_map_.keys())

    @classmethod
    def literal(cls):
        return Literal[cls.get_values()]


class IntEnum(int, BaseEnum):

    def __new__(cls, value):
        obj = int.__new__(cls, value)
        obj._value_ = value
        return obj


class StrEnum(str, BaseEnum):

    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj
