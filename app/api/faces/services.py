import asyncio
import os
import typing as t
from datetime import datetime, timezone

import aiofiles
import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status

from config import APP_SETTINGS
from config.qdrant import qdrant_db
from resources.detection.engine import analyze_face_image
from resources.repositories import FacesRepository
from .schemas import FaceUser


def point_id_for_user(user_id: str) -> str:
    return FacesRepository.point_id_for_user(user_id)


def get_faces_repository() -> FacesRepository:
    return FacesRepository(qdrant_db.client)


def validate_user_fields(user_id: str, full_name: str) -> t.Tuple[str, str]:
    user_id = user_id.strip()
    full_name = full_name.strip()
    if not user_id or len(user_id) > 128:
        raise HTTPException(status_code=422, detail='User ID 1–128 belgidan iborat bo‘lsin.')
    if not full_name or len(full_name) > 200:
        raise HTTPException(status_code=422, detail='To‘liq ism 1–200 belgidan iborat bo‘lsin.')
    return user_id, full_name


async def check_user_id_available(user_id: str) -> None:
    if await get_faces_repository().user_id_exists(user_id):
        raise HTTPException(status_code=409, detail='Bu User ID allaqachon mavjud.')


async def save_face_sample(
        user_id: str, full_name: str, embedding: np.ndarray, frame: np.ndarray
) -> FaceUser:
    await check_user_id_available(user_id)
    repository = get_faces_repository()
    duplicate = await repository.find_duplicate(embedding.tolist())
    if duplicate is not None:
        matched = duplicate.payload or {}
        raise HTTPException(
            status_code=409,
            detail=f"Bu yuz bazada mavjud: {matched.get('full_name', 'noma’lum user')}.",
        )

    point_id = point_id_for_user(user_id)
    image_name = f'{point_id}.jpg'
    image_path = APP_SETTINGS.FACE_IMAGES_DIR / image_name
    encoded, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not encoded:
        raise HTTPException(status_code=500, detail='Rasmni saqlab bo‘lmadi.')
    async with aiofiles.open(image_path, 'wb') as output:
        await output.write(jpeg.tobytes())

    image_url = f'/{APP_SETTINGS.MEDIA_URL.strip("/")}/faces/{image_name}'
    payload = {
        'user_id': user_id,
        'full_name': full_name,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'image_url': image_url,
    }
    try:
        await repository.create_face(user_id, embedding.tolist(), payload)
    except Exception:
        image_path.unlink(missing_ok=True)
        raise
    return payload_to_user(point_id, payload)


def payload_to_user(point_id: str, payload: t.Dict) -> FaceUser:
    created_at_value = payload.get('created_at')
    created_at = (
        datetime.fromisoformat(str(created_at_value))
        if created_at_value
        else datetime.fromtimestamp(0, timezone.utc)
    )
    return FaceUser(
        id=point_id,
        user_id=str(payload['user_id']),
        full_name=str(payload['full_name']),
        created_at=created_at,
        image_url=payload.get('image_url'),
    )


async def list_face_users() -> t.List[FaceUser]:
    users: t.List[FaceUser] = []
    points = await get_faces_repository().list_all()
    for point in points:
        if point.payload and point.payload.get('user_id') is not None:
            users.append(payload_to_user(str(point.id), point.payload))

    return sorted(users, key=lambda user: user.created_at, reverse=True)


async def enroll_face_user(
        user_id: str,
        full_name: str,
        image: UploadFile,
) -> FaceUser:
    user_id = user_id.strip()
    full_name = full_name.strip()
    if not user_id or len(user_id) > 128:
        raise HTTPException(status_code=422, detail='User ID 1–128 belgidan iborat bo‘lsin.')
    if not full_name or len(full_name) > 200:
        raise HTTPException(status_code=422, detail='To‘liq ism 1–200 belgidan iborat bo‘lsin.')
    if image.content_type not in APP_SETTINGS.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail='Faqat JPEG, PNG yoki WebP rasm yuboring.')

    content = await image.read(APP_SETTINGS.MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail='Rasm bo‘sh.')
    if len(content) > APP_SETTINGS.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail='Rasm hajmi 8 MB dan oshmasin.')

    frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail='Rasmni o‘qib bo‘lmadi.')

    faces = await asyncio.to_thread(analyze_face_image, frame)
    if not faces:
        raise HTTPException(status_code=422, detail='Rasmda yuz topilmadi.')
    if len(faces) != 1:
        raise HTTPException(status_code=422, detail='Kadrda faqat bitta yuz bo‘lishi kerak.')

    face = faces[0]
    x1, y1, x2, y2 = face.bbox
    if min(x2 - x1, y2 - y1) < APP_SETTINGS.MIN_FACE_SIZE:
        raise HTTPException(
            status_code=422,
            detail='Yuz juda kichik. Kameraga yaqinroq turing.',
        )
    if face.normed_embedding is None:
        raise HTTPException(status_code=422, detail='Yuz embeddingini olib bo‘lmadi.')

    repository = get_faces_repository()
    point_id = point_id_for_user(user_id)
    if await repository.user_id_exists(user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Bu User ID bilan foydalanuvchi allaqachon mavjud.',
        )

    image_name = f'{point_id}.jpg'
    image_path = APP_SETTINGS.FACE_IMAGES_DIR / image_name
    encoded, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not encoded:
        raise HTTPException(status_code=500, detail='Rasmni saqlashda xatolik yuz berdi.')

    async with aiofiles.open(image_path, 'wb') as output:
        await output.write(jpeg.tobytes())

    created_at = datetime.now(timezone.utc)
    image_url = f'/{APP_SETTINGS.MEDIA_URL.strip("/")}/faces/{image_name}'
    payload = {
        'user_id': user_id,
        'full_name': full_name,
        'created_at': created_at.isoformat(),
        'image_url': image_url,
    }
    try:
        await repository.create_face(user_id, face.normed_embedding.tolist(), payload)
    except Exception:
        image_path.unlink(missing_ok=True)
        raise

    return payload_to_user(point_id, payload)


async def delete_face_user(user_id: str) -> None:
    repository = get_faces_repository()
    point_id = point_id_for_user(user_id)
    if not await repository.delete_by_user_id(user_id):
        raise HTTPException(status_code=404, detail='Foydalanuvchi topilmadi.')
    image_path = APP_SETTINGS.FACE_IMAGES_DIR / f'{point_id}.jpg'
    if image_path.exists():
        await asyncio.to_thread(os.remove, image_path)
