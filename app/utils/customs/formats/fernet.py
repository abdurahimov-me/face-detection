from dataclasses import dataclass

from pydantic_core import core_schema

from utils.security import fernet
from .base import BaseFormat


@dataclass(frozen=True)
class UserEncrypt(BaseFormat):
    user_id: int
    tenant: str

    def get_both(self):
        return self.user_id, self.tenant

    json_schema = {
        "type": "string",
        "format": "fernet-encrypted",
        "description": "Fernet encrypted value"
    }

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.union_schema([
            core_schema.none_schema(),
            core_schema.no_info_after_validator_function(
                cls.validate,
                core_schema.str_schema()
            )
        ])

    @classmethod
    def validate(cls, v: str = None, *args, **kwargs):
        try:
            decrypted = fernet.decrypt(v)

            if isinstance(decrypted, bytes):
                decrypted = decrypted.decode()
            user_id, tenant = decrypted.split(':')
            return cls(user_id=int(user_id), tenant=tenant)
        except Exception as e:
            raise ValueError(f"Invalid encrypted value: {e}")


    def __repr__(self):
        return f"{self.__class__.__name__}({self.user_id}, {self.tenant})"