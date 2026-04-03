from pydantic import BaseModel
from utils.customs.formats.fernet import FernetEncrypt


class StartConversation(BaseModel):
    partner: FernetEncrypt
