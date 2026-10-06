from fastapi import APIRouter

from .schemas import EnrollmentOffer, WebRTCAnswer, WebRTCOffer
from .services import create_enrollment_answer, create_webrtc_answer


router = APIRouter(prefix='/webrtc', tags=['WebRTC'])


@router.post('/offer', response_model=WebRTCAnswer)
async def offer(payload: WebRTCOffer) -> WebRTCAnswer:
    answer = await create_webrtc_answer(payload.sdp, payload.type)
    return WebRTCAnswer(sdp=answer.sdp, type=answer.type)


@router.post('/enroll/offer', response_model=WebRTCAnswer)
async def enrollment_offer(payload: EnrollmentOffer) -> WebRTCAnswer:
    answer = await create_enrollment_answer(
        payload.sdp, payload.type, payload.user_id, payload.full_name
    )
    return WebRTCAnswer(sdp=answer.sdp, type=answer.type)
