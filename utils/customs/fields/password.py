from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from utils.security.hash import make_pass


class PasswordField(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value.startswith('$argon2id$v=19$m=65536'):
            return value
        return make_pass(value)

    def process_result_value(self, value, dialect) -> str:
        return value
