from pydantic import BaseModel

from utils.customs.formats.fernet import UserEncrypt


class StartConversation(BaseModel):
    partner: UserEncrypt
