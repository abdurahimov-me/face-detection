__all__ = (
    'get_token_payload_or_none',
    'get_token_payload',
    'payload_or_none',
    'token_payload',
)

from typing import Union, Annotated, Optional

import jwt
from fastapi import Depends, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from utils.jwt import decode_jwt, Payload

http_bearer = HTTPBearer(auto_error=True)


def get_token_payload_or_none(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> Union[Payload, None]:
    try:

        if credentials:
            payload = decode_jwt(credentials.credentials)
            return Payload.from_dict(**payload)
        return None

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token expired",
        )

    except (jwt.InvalidTokenError, jwt.DecodeError):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials",
        )


def get_token_payload(
        payload=Depends(get_token_payload_or_none),
) -> Union[Payload, None]:
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return payload


payload_or_none = Annotated[Optional[Payload], Depends(get_token_payload_or_none)]
token_payload = Annotated[Payload, Depends(get_token_payload)]
