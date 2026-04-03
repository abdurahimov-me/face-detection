from utils.security import fernet
from .base import BaseFormat


class FernetEncrypt(BaseFormat):
    json_schema = {"type": "str", "format": "str", "description": "Fernet encryption key."}

    @classmethod
    def validate(cls, v=None, *args, **kwargs):
        if v:
            try:
                return fernet.decrypt(v)
            except Exception:
                return None
        return None
