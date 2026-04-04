from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from typing import Optional, Any, Union

import jwt

from config import JWT_SETTINGS
from .utility import now


@dataclass(frozen=True, slots=True)
class Payload:
    iat: int
    exp: int
    user_id: int
    tenant: str

    @classmethod
    def from_dict(cls, data: dict) -> "Payload":
        return cls(
            iat=data["iat"],
            exp=data["exp"],
            user_id=int(data["user_id"]),
            tenant=data["schema_name"],
        )


def encode_jwt(
        payload: dict,
        algorithm=JWT_SETTINGS.ALGORITHM,
        secret_key: str = JWT_SETTINGS.JWT_SECRET_KEY,
        expiration: timedelta = JWT_SETTINGS.ACCESS_TOKEN_EXPIRE,
):
    payload.update(
        exp=now() + expiration,
        iat=now(),
    )

    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm,
    )


def decode_jwt(
        token: str,
        secret_key: str = JWT_SETTINGS.JWT_SECRET_KEY,
        algorithm: str = JWT_SETTINGS.ALGORITHM,
):
    return jwt.decode(
        token,
        secret_key,
        algorithms=[algorithm],
    )


def get_decoded(
        token: str
) -> Union[dict, None]:
    try:
        return decode_jwt(token)
    except (jwt.InvalidTokenError, jwt.DecodeError, jwt.ExpiredSignatureError):
        return None


class JWT:
    def __init__(
            self,
            obj: Optional[Any] = None,
            payload: Optional[dict] = None,
            sub: Optional[str] = 'id',
            payload_fields: Optional[tuple] = JWT_SETTINGS.JWT_PAYLOAD_FIELDS,
    ):
        self.payload = self.set_payload(obj, sub, payload, payload_fields)
        self.secret_key = JWT_SETTINGS.JWT_SECRET_KEY
        self.algorithm = JWT_SETTINGS.ALGORITHM
        self.access_token_expire = JWT_SETTINGS.ACCESS_TOKEN_EXPIRE

    @classmethod
    def set_payload(cls, obj, sub, payload, payload_fields):
        if payload and payload.get('sub'):
            return payload
        elif obj and sub and payload_fields:
            payload = {field: getattr(obj, field) for field in payload_fields}
            payload['sub'] = str(getattr(obj, sub))
            return payload
        else:
            raise ValueError('payload must have sub or obj')

    @cached_property
    def access(self) -> str:
        return encode_jwt(
            payload=self.payload,
            secret_key=self.secret_key,
            algorithm=self.algorithm,
            expiration=self.access_token_expire,
        )
