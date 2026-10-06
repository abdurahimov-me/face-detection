from datetime import datetime

from pydantic import BaseModel


class FaceUser(BaseModel):
    id: str
    user_id: str
    full_name: str
    created_at: datetime
    image_url: str | None = None
