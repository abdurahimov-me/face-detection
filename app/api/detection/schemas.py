from pydantic import BaseModel


class WebRTCOffer(BaseModel):
    sdp: str
    type: str


class WebRTCAnswer(BaseModel):
    sdp: str
    type: str


class EnrollmentOffer(WebRTCOffer):
    user_id: str
    full_name: str
