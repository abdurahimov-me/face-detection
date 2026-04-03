from cryptography.fernet import Fernet
from config.settings import APP_SETTINGS
print(APP_SETTINGS.FERNET_SECRET_KEY)

fernet = Fernet(APP_SETTINGS.FERNET_SECRET_KEY.encode())


def encrypt(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()