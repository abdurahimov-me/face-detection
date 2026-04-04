from datetime import datetime
from zoneinfo import ZoneInfo

from config import APP_SETTINGS


def now(timezone: str = APP_SETTINGS.TIME_ZONE):
    return datetime.now(ZoneInfo(timezone))


def utcnow():
    return datetime.now(ZoneInfo('UTC'))
