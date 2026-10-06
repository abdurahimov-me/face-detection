import asyncio
import json
import os
import time
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

import aiofiles
import cv2
import numpy as np
from aiortc.mediastreams import MediaStreamError
from fastapi import HTTPException, UploadFile, status
from qdrant_client import models

from api.detection.services import (
    analyze_face_image,
    ensure_faces_collection,
)
from config import APP_SETTINGS
from config.qdrant import qdrant_db
from .schemas import FaceUser


def point_id_for_user(user_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f'face-user:{user_id}'))


def validate_user_fields(user_id: str, full_name: str) -> tuple[str, str]:
    user_id = user_id.strip()
    full_name = full_name.strip()
    if not user_id or len(user_id) > 128:
        raise HTTPException(status_code=422, detail='User ID 1–128 belgidan iborat bo‘lsin.')
    if not full_name or len(full_name) > 200:
        raise HTTPException(status_code=422, detail='To‘liq ism 1–200 belgidan iborat bo‘lsin.')
    return user_id, full_name


async def check_user_id_available(user_id: str) -> None:
    existing = await qdrant_db.client.retrieve(
        collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
        ids=[point_id_for_user(user_id)],
        with_payload=False,
        with_vectors=False,
    )
    if existing:
        raise HTTPException(status_code=409, detail='Bu User ID allaqachon mavjud.')


async def save_face_sample(
        user_id: str, full_name: str, embedding: np.ndarray, frame: np.ndarray
) -> FaceUser:
    await check_user_id_available(user_id)
    duplicate = await qdrant_db.client.query_points(
        collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
        query=embedding.tolist(),
        limit=1,
        score_threshold=APP_SETTINGS.MIN_DUPLICATE_SIMILARITY,
        with_payload=True,
    )
    if duplicate.points:
        matched = duplicate.points[0].payload or {}
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
        await qdrant_db.client.upsert(
            collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
            points=[models.PointStruct(id=point_id, vector=embedding.tolist(), payload=payload)],
            wait=True,
        )
    except Exception:
        image_path.unlink(missing_ok=True)
        raise
    return payload_to_user(point_id, payload)


def inspect_enrollment_frame(frame: np.ndarray):
    height, width = frame.shape[:2]
    if width > 640:
        frame = cv2.resize(frame, (640, round(height * 640 / width)))
    faces = analyze_face_image(frame)
    if len(faces) != 1:
        return None, frame, 'Kadrda faqat bitta yuz bo‘lsin.' if faces else 'Yuz kutilmoqda.'
    face = faces[0]
    x1, y1, x2, y2 = face.bbox.astype(int)
    if min(x2 - x1, y2 - y1) < APP_SETTINGS.MIN_FACE_SIZE:
        return None, frame, 'Kameraga yaqinroq turing.'
    crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if not 55 <= float(gray.mean()) <= 210:
        return None, frame, 'Yuzni yaxshiroq yoritib oling.'
    if cv2.Laplacian(gray, cv2.CV_64F).var() < APP_SETTINGS.MIN_SHARPNESS:
        return None, frame, 'Kamerani qimirlatmay turing.'
    if face.normed_embedding is None:
        return None, frame, 'Yuzni to‘g‘ri kameraga qarating.'
    return face.normed_embedding.astype(np.float32), frame, None


class EnrollmentSession:
    def __init__(self, user_id: str, full_name: str) -> None:
        self.user_id = user_id
        self.full_name = full_name

    async def consume(self, track, channel_holder: dict) -> None:
        embeddings: list[np.ndarray] = []
        best_frame: np.ndarray | None = None
        last_sample = 0.0
        started = time.monotonic()

        def send(event: str, message: str, **extra) -> None:
            channel = channel_holder.get('channel')
            if channel is not None and channel.readyState == 'open':
                channel.send(json.dumps({
                    'event': event, 'message': message,
                    'collected': len(embeddings), 'total': APP_SETTINGS.ENROLLMENT_SAMPLES, **extra,
                }))

        try:
            await check_user_id_available(self.user_id)
            while len(embeddings) < APP_SETTINGS.ENROLLMENT_SAMPLES:
                frame = await track.recv()
                now = time.monotonic()
                if now - started > APP_SETTINGS.ENROLLMENT_TIMEOUT_SECONDS:
                    send('error', 'Sifatli kadrlar yig‘ilmadi. Qayta urinib ko‘ring.')
                    return
                if now - last_sample < APP_SETTINGS.ENROLLMENT_INTERVAL_SECONDS:
                    continue
                last_sample = now
                vector, image, reason = await asyncio.to_thread(
                    inspect_enrollment_frame, frame.to_ndarray(format='bgr24')
                )
                if vector is None:
                    send('progress', reason)
                    continue
                if embeddings and float(np.dot(vector, embeddings[0])) < APP_SETTINGS.MIN_SAMPLE_SIMILARITY:
                    send('progress', 'Bir xil yuz kamerada tursin.')
                    continue
                embeddings.append(vector)
                if best_frame is None or len(embeddings) == APP_SETTINGS.ENROLLMENT_SAMPLES // 2 + 1:
                    best_frame = image.copy()
                send('progress', 'Sifatli kadr qabul qilindi.')

            mean = np.mean(embeddings, axis=0)
            norm = np.linalg.norm(mean)
            if norm <= 0:
                send('error', 'Yuz embeddingini hisoblab bo‘lmadi.')
                return
            mean = mean / norm
            send('saving', 'User saqlanmoqda.')
            user = await save_face_sample(
                self.user_id, self.full_name, mean, best_frame
            )
            send('complete', 'User bazaga qo‘shildi.', user=user.model_dump(mode='json'))
        except MediaStreamError:
            return
        except asyncio.CancelledError:
            raise
        except HTTPException as exc:
            send('error', str(exc.detail))
        except Exception:
            send('error', 'Serverda xatolik yuz berdi. Qayta urinib ko‘ring.')
            raise


def payload_to_user(point_id: str, payload: dict) -> FaceUser:
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


async def list_face_users() -> list[FaceUser]:
    await ensure_faces_collection()
    users: list[FaceUser] = []
    offset = None

    while True:
        points, offset = await qdrant_db.client.scroll(
            collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            if point.payload and point.payload.get('user_id') is not None:
                users.append(payload_to_user(str(point.id), point.payload))
        if offset is None:
            break

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

    await ensure_faces_collection()
    point_id = point_id_for_user(user_id)
    existing = await qdrant_db.client.retrieve(
        collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
        ids=[point_id],
        with_payload=True,
        with_vectors=False,
    )
    if existing:
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
        await qdrant_db.client.upsert(
            collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=face.normed_embedding.tolist(),
                    payload=payload,
                )
            ],
            wait=True,
        )
    except Exception:
        image_path.unlink(missing_ok=True)
        raise

    return payload_to_user(point_id, payload)


async def delete_face_user(user_id: str) -> None:
    await ensure_faces_collection()
    point_id = point_id_for_user(user_id)
    records = await qdrant_db.client.retrieve(
        collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
        ids=[point_id],
        with_payload=True,
        with_vectors=False,
    )
    if not records:
        raise HTTPException(status_code=404, detail='Foydalanuvchi topilmadi.')

    await qdrant_db.client.delete(
        collection_name=APP_SETTINGS.FACES_COLLECTION_NAME,
        points_selector=models.PointIdsList(points=[point_id]),
        wait=True,
    )
    image_path = APP_SETTINGS.FACE_IMAGES_DIR / f'{point_id}.jpg'
    if image_path.exists():
        await asyncio.to_thread(os.remove, image_path)
