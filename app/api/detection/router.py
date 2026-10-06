from fastapi import APIRouter

from api.shared.schemas import WebRTCAnswer, WebRTCOffer
from .services import  create_webrtc_answer


router = APIRouter(prefix='/detection', tags=['WebRTC'])


@router.post('/offer', response_model=WebRTCAnswer)
async def offer(payload: WebRTCOffer) -> WebRTCAnswer:
    answer = await create_webrtc_answer(payload.sdp, payload.type)
    return WebRTCAnswer(sdp=answer.sdp, type=answer.type)

