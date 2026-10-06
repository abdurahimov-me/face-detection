from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from .schemas import FaceUser
from .services import delete_face_user, enroll_face_user, list_face_users


router = APIRouter(prefix='/faces', tags=['Faces'])



@router.post('/enroll/offer', response_model=WebRTCAnswer)
async def enrollment_offer(payload: EnrollmentOffer) -> WebRTCAnswer:
    answer = await create_enrollment_answer(
        payload.sdp, payload.type, payload.user_id, payload.full_name
    )
    return WebRTCAnswer(sdp=answer.sdp, type=answer.type)


@router.get('', response_model=list[FaceUser])
async def get_faces() -> list[FaceUser]:
    return await list_face_users()


@router.post('', response_model=FaceUser, status_code=status.HTTP_201_CREATED)
async def create_face(
    user_id: Annotated[str, Form()],
    full_name: Annotated[str, Form()],
    image: Annotated[UploadFile, File()],
) -> FaceUser:
    return await enroll_face_user(user_id, full_name, image)


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_face(user_id: str) -> Response:
    await delete_face_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
