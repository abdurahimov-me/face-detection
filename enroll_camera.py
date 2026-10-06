"""Capture one face from a webcam and enroll it in the local Qdrant collection.

Usage:
    python enroll_camera.py 123 "Ali Valiyev"
    python enroll_camera.py 123 "Ali Valiyev" --camera 1

Press SPACE to capture a frame, or Q / ESC to cancel.
"""

import argparse
import asyncio
import os
import time
import uuid

import cv2
from insightface.app import FaceAnalysis


QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION = "faces"
EMBEDDING_SIZE = 512
DETECTION_SIZE = (320, 320)
USER_POINT_NAMESPACE = uuid.UUID("e8a5e26a-d30f-41d4-9b94-d7b61074d135")
TIMING_LOG_EVERY_N_FRAMES = 30


def log_timing(label: str, elapsed_seconds: float) -> None:
    print(f"[vaqt] {label}: {elapsed_seconds * 1000:.1f} ms", flush=True)


def create_face_engine() -> FaceAnalysis:
    engine = FaceAnalysis(name="buffalo_m", providers=["CPUExecutionProvider"])
    engine.prepare(ctx_id=-1, det_size=DETECTION_SIZE)
    return engine


def create_qdrant_client():
    from qdrant_client import AsyncQdrantClient

    return AsyncQdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=5,
    )


async def ensure_collection(client) -> None:
    from qdrant_client import models

    collections = await client.get_collections()
    if COLLECTION not in {item.name for item in collections.collections}:
        await client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_SIZE,
                distance=models.Distance.COSINE,
            ),
        )


async def enroll_from_camera(user_id: str, full_name: str, camera_index: int) -> None:
    from qdrant_client import models

    started = time.perf_counter()
    engine = create_face_engine()
    log_timing("modelni yuklash", time.perf_counter() - started)
    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        raise RuntimeError(f"Kamerani ochib bo'lmadi (index: {camera_index})")

    client = create_qdrant_client()
    try:
        started = time.perf_counter()
        await ensure_collection(client)
        log_timing("Qdrant kolleksiyasini tekshirish", time.perf_counter() - started)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print("Yuzni kameraga qarating. SPACE — saqlash, Q/ESC — bekor qilish.")
        frame_count = 0
        inference_total = 0.0
        timing_started = time.perf_counter()

        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Kameradan tasvir olib bo'lmadi")

            preview = frame.copy()
            inference_started = time.perf_counter()
            faces = engine.get(frame)
            inference_elapsed = time.perf_counter() - inference_started
            frame_count += 1
            inference_total += inference_elapsed
            if frame_count >= TIMING_LOG_EVERY_N_FRAMES:
                elapsed = time.perf_counter() - timing_started
                print(
                    f"[vaqt, oxirgi {frame_count} kadr] "
                    f"detect+embedding={inference_total * 1000 / frame_count:.1f} ms/kadr, "
                    f"FPS={frame_count / elapsed:.1f}",
                    flush=True,
                )
                frame_count = 0
                inference_total = 0.0
                timing_started = time.perf_counter()
            for face in faces:
                x1, y1, x2, y2 = (int(value) for value in face.bbox)
                cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 220, 0), 2)

            instruction = (
                f"Yuzlar: {len(faces)} | SPACE: saqlash | Q/ESC: chiqish"
                if len(faces) == 1
                else f"Yuzlar: {len(faces)} | Kadrda faqat bitta yuz bo'lsin"
            )
            cv2.putText(
                preview,
                instruction,
                (12, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 220, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow("Yuzni bazaga qoshish", preview)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):
                print("Bekor qilindi; bazaga yozilmadi.")
                return
            if key == ord(" "):
                if len(faces) != 1:
                    print("Saqlanmadi: kadrda aynan bitta yuz bo'lishi kerak.")
                    continue

                point_id = str(uuid.uuid5(USER_POINT_NAMESPACE, user_id))
                upsert_started = time.perf_counter()
                await client.upsert(
                    collection_name=COLLECTION,
                    points=[
                        models.PointStruct(
                            id=point_id,
                            vector=faces[0].normed_embedding.tolist(),
                            payload={"user_id": user_id, "full_name": full_name},
                        )
                    ],
                )
                log_timing("Qdrant'ga yozish", time.perf_counter() - upsert_started)
                print(f"Bazaga yozildi: {full_name} (ID: {user_id})")
                return
    finally:
        camera.release()
        cv2.destroyAllWindows()
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kameradan yuzni Qdrant'ga yozish")
    parser.add_argument("user_id", help="Foydalanuvchi ID si")
    parser.add_argument("full_name", help="Foydalanuvchining to'liq ismi")
    parser.add_argument("--camera", type=int, default=0, help="Kamera indexi (default: 0)")
    args = parser.parse_args()
    asyncio.run(enroll_from_camera(args.user_id, args.full_name, args.camera))


if __name__ == "__main__":
    main()
