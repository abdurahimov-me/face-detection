from fastapi import HTTPException


class BadRequest(HTTPException):
    def __init__(self, detail="Bad request", *args, **kwargs):
        super().__init__(status_code=400, detail=detail, *args, **kwargs)


class WSException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
