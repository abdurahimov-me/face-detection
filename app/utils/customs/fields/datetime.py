from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class DateTimeField(TypeDecorator):
    """
    A DateTime type that ensures all times are stored in UTC.
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Called when saving the value to the database.

        Ensures the datetime is tz-aware and in UTC.
        """
        if value is None:
            return value

        if not isinstance(value, datetime):
            raise ValueError(f"Expected a datetime object, got {type(value)}")

        if value.tzinfo is None:
            raise ValueError("Naive datetime (no timezone) is not allowed.")

        return value.astimezone(ZoneInfo("UTC"))

    def __repr__(self):
        return "DateTimeField()"
