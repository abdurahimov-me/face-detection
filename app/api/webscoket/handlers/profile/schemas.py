from pydantic import BaseModel
from uuid import UUID



class MarkAsTyping(BaseModel):
    conversation_uuid: UUID