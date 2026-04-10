from pydantic_core import core_schema

from utils.security import fernet
from .base import BaseFormat


class FernetEncrypt(str, BaseFormat):
    json_schema = {
        "type": "string",
        "format": "fernet-encrypted",
        "description": "Fernet encrypted value"
    }

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema()
        )

    @classmethod
    def validate(cls, v=None, *args, **kwargs):
        try:
            decrypted = fernet.decrypt(v)

            if isinstance(decrypted, bytes):
                decrypted = decrypted.decode()

            return cls(decrypted)
        except Exception as e:
            raise ValueError(f"Invalid encrypted value: {e}")
