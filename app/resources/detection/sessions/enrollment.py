import asyncio
import json
import time
import typing as t

import cv2
import numpy as np
from aiortc.mediastreams import MediaStreamError
from fastapi import HTTPException

from config import APP_SETTINGS
from ..engine import analyze_face_image


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
    def __init__(
        self,
        user_id: str,
        full_name: str,
        check_available: t.Callable[[str], t.Awaitable[None]],
        save_sample: t.Callable[..., t.Awaitable],
    ) -> None:
        self.user_id = user_id
        self.full_name = full_name
        self.check_available = check_available
        self.save_sample = save_sample

    async def consume(self, track, channel_holder: t.Dict) -> None:
        embeddings: t.List[np.ndarray] = []
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
            await self.check_available(self.user_id)
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
            user = await self.save_sample(
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
