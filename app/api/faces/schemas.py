from datetime import datetime

from pydantic import BaseModel
from api.shared.schemas import WebRTCOffer


class FaceUser(BaseModel):
    id: str
    user_id: str
    full_name: str
    created_at: datetime
    image_url: str | None = None


class EnrollmentOffer(WebRTCOffer):
    user_id: str
    full_name: str
