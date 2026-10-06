import asyncio
import json
import time

import numpy as np
from aiortc.mediastreams import MediaStreamError
from fastapi import HTTPException

from config import APP_SETTINGS


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
