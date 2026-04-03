import typing as t

from pydantic import BaseModel


class BaseWSResponse(BaseModel):
    success: bool = False
    request_id: t.Any = None
    command: str
    data: t.Any = None
