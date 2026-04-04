from datetime import datetime, date
from typing import Tuple, Literal
from zoneinfo import ZoneInfo

from config import APP_SETTINGS
from .base import BaseFormat


class BaseDatetime(BaseFormat):
    json_schema = {"type": "datetime", "format": "datetime", "description": "Datetime to the field."}
    format = '%Y-%m-%d %H:%M:%S'
    timezone = APP_SETTINGS.TIME_ZONE
    is_instances: Tuple = (datetime, date)
    validate_type: Literal['response', 'request'] = None

    @classmethod
    def validate(cls, v=None, *args, **kwargs):
        return {
            'response': cls.validate_response,
            'request': cls.validate_request
        }[cls.validate_type](v, *args, **kwargs)

    @classmethod
    def validate_request(cls, v=None, *args, **kwargs):
        if isinstance(v, str):
            try:
                v = datetime.strptime(v, cls.format)
            except ValueError:
                raise ValueError(f"Invalid date format. Expected format: {cls.format}")
        elif not isinstance(v, (datetime, date)):
            raise TypeError('The value should be a datetime.datetime, datetime.date, or a valid date string')
        return v.astimezone(ZoneInfo(cls.timezone)) if isinstance(v, datetime) else v

    @classmethod
    def validate_response(cls, v=None, *args, **kwargs):
        if not isinstance(v, (datetime, date)):
            raise TypeError('The value should be a datetime.datetime or datetime.date')
        v = v.astimezone(ZoneInfo(APP_SETTINGS.TIME_ZONE))
        return v.strftime(cls.format) if cls.format else v


class DateTime(BaseDatetime):
    json_schema = {"type": "date", "format": "date", "description": "Datetime to the field."}
    validate_type = 'response'
    format = None


class Date(BaseDatetime):
    json_schema = {"type": "date", "format": "date", "description": "Datetime to the field."}
    format = "%Y-%m-%d"
    validate_type = 'response'
