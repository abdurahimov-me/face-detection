"""Minimal face enrollment and real-time recognition example.

Usage:
    python test1.py register 123 "Ali Valiyev" face.jpg
    python test1.py camera

The InsightFace buffalo_l model detects faces and creates 512-dimensional
face embeddings. Qdrant stores those vectors and searches for a match.
"""

import argparse
import asyncio
import os
import time
import uuid
from dataclasses import dataclass

import cv2
import numpy as np
import supervision as sv
from insightface.app import FaceAnalysis
from insightface.app.common import Face
from trackers import ByteTrackTracker


QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION = "faces"
EMBEDDING_SIZE = 512
MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.55"))
USER_POINT_NAMESPACE = uuid.UUID("e8a5e26a-d30f-41d4-9b94-d7b61074d135")
DETECT_EVERY_N_FRAMES = 3
DETECTION_SIZE = (320, 320)
CAMERA_DETECTION_THRESHOLD = 0.25
TRACK_MAX_MISSING_FRAMES = 30
TIMING_LOG_EVERY_N_FRAMES = 30
TRACKER_FPS = 10.0


def log_timing(label: str, elapsed_seconds: float) -> None:
    print(f"[vaqt] {label}: {elapsed_seconds * 1000:.1f} ms", flush=True)


@dataclass
class FaceTrack:
    track_id: int
    bbox: tuple[float, float, float, float]
    last_seen: int
    name: str = "Noma'lum"
    score: float | None = None
    recognized: bool = False


def create_face_engine(det_threshold: float = 0.5) -> FaceAnalysis:
    """Load only the detector and recognizer from buffalo_m on CPU."""
    engine = FaceAnalysis(
        name="buffalo_m",
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"],
    )
    engine.prepare(
        ctx_id=-1,
        det_thresh=det_threshold,
        det_size=DETECTION_SIZE,
    )
    return engine


def create_qdrant_client():
    from qdrant_client import AsyncQdrantClient

    return AsyncQdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
        api_key=QDRANT_API_KEY,
        timeout=5,
    )


def create_sync_qdrant_client():
    from qdrant_client import QdrantClient

    return QdrantClient(
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


def search_face_in_qdrant(client, embedding: list[float]):
    """Run vector search in a worker thread, outside the camera event loop."""
    started = time.perf_counter()
    result = client.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=1,
        score_threshold=MATCH_THRESHOLD,
        with_payload=True,
    )
    return result, time.perf_counter() - started


def get_single_face(engine: FaceAnalysis, image):
    faces = engine.get(image)
    if len(faces) != 1:
        raise ValueError(
            f"Rasmda aynan bitta yuz bo'lishi kerak; topilgan yuzlar: {len(faces)}"
        )
    return faces[0]


async def register_user(user_id: str, full_name: str, image_path: str) -> None:
    from qdrant_client import models

    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Rasmni o'qib bo'lmadi: {image_path}")

    started = time.perf_counter()
    engine = create_face_engine()
    log_timing("modelni yuklash", time.perf_counter() - started)
    started = time.perf_counter()
    face = get_single_face(engine, image)
    log_timing("yuz aniqlash + embedding", time.perf_counter() - started)
    point_id = str(uuid.uuid5(USER_POINT_NAMESPACE, user_id))
    client = create_qdrant_client()
    try:
        started = time.perf_counter()
        await ensure_collection(client)
        log_timing("Qdrant kolleksiyasini tekshirish", time.perf_counter() - started)
        started = time.perf_counter()
        await client.upsert(
            collection_name=COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=face.normed_embedding.tolist(),
                    payload={"user_id": user_id, "full_name": full_name},
                )
            ],
        )
        log_timing("Qdrant'ga yozish", time.perf_counter() - started)
        print(f"Ro'yxatdan o'tkazildi: {full_name} (ID: {user_id})")
    finally:
        await client.close()


async def recognize_camera() -> None:
    """Recognize faces from the camera using CPU inference and Qdrant search."""
    started = time.perf_counter()
    engine = create_face_engine(det_threshold=CAMERA_DETECTION_THRESHOLD)
    log_timing("modelni yuklash", time.perf_counter() - started)
    client = create_qdrant_client()
    search_client = create_sync_qdrant_client()
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        search_client.close()
        await client.close()
        raise RuntimeError("Kamerani ochib bo'lmadi")

    pending_queries: dict[int, asyncio.Task] = {}
    try:
        await ensure_collection(client)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        tracks: dict[int, FaceTrack] = {}
        tracker = ByteTrackTracker(
            frame_rate=TRACKER_FPS,
            lost_track_buffer=30,
            track_activation_threshold=0.5,
            minimum_consecutive_frames=2,
            minimum_iou_threshold=0.1,
            high_conf_det_threshold=0.5,
        )
        frame_number = 0
        stats_started = time.perf_counter()
        stats_frames = 0
        stats_read = 0.0
        stats_detection = 0.0
        stats_embedding = 0.0
        stats_tracking = 0.0
        stats_detection_calls = 0
        stats_embedding_calls = 0
        stats_qdrant = 0.0
        stats_loop = 0.0

        while True:
            loop_started = time.perf_counter()
            read_started = time.perf_counter()
            ok, frame = camera.read()
            read_elapsed = time.perf_counter() - read_started
            if not ok:
                break

            frame_number += 1
            stats_frames += 1
            stats_read += read_elapsed

            # Apply Qdrant results that completed in the background.
            for track_id, task in list(pending_queries.items()):
                if not task.done():
                    continue
                del pending_queries[track_id]
                try:
                    result, query_elapsed = task.result()
                    stats_qdrant += query_elapsed
                    log_timing(
                        f"track #{track_id} Qdrant background qidiruvi",
                        query_elapsed,
                    )
                    track = tracks.get(track_id)
                    if track is None:
                        continue
                    if result.points:
                        match = result.points[0]
                        payload = match.payload or {}
                        track.name = payload.get("full_name", "Noma'lum")
                        track.score = float(match.score)
                    else:
                        track.name = "Noma'lum"
                        track.score = None
                    track.recognized = True
                except Exception as error:
                    track = tracks.get(track_id)
                    if track is not None:
                        track.name = "Qdrant xatosi"
                    print(
                        f"[xato] track #{track_id} Qdrant: {error}",
                        flush=True,
                    )

            if frame_number % DETECT_EVERY_N_FRAMES == 0:
                detection_started = time.perf_counter()
                bboxes, keypoints = engine.det_model.detect(frame)
                detection_elapsed = time.perf_counter() - detection_started
                stats_detection += detection_elapsed
                stats_detection_calls += 1
                detection_data = {}
                if keypoints is not None:
                    detection_data["face_keypoints"] = keypoints
                detections = sv.Detections(
                    xyxy=bboxes[:, :4].astype(np.float32),
                    confidence=bboxes[:, 4].astype(np.float32),
                    data=detection_data,
                )
                tracking_started = time.perf_counter()
                tracked_detections = tracker.update(detections)
                stats_tracking += time.perf_counter() - tracking_started

                for detection_index in range(len(tracked_detections)):
                    byte_track_id = int(tracked_detections.tracker_id[detection_index])
                    if byte_track_id < 0:
                        continue
                    detected_box = tracked_detections.xyxy[detection_index]
                    box = tuple(float(value) for value in detected_box)

                    if byte_track_id not in tracks:
                        track = FaceTrack(
                            track_id=byte_track_id,
                            bbox=box,
                            last_seen=frame_number,
                        )
                        tracks[byte_track_id] = track

                        # Only a newly-created track needs a face embedding.
                        tracked_keypoints = tracked_detections.data.get(
                            "face_keypoints"
                        )
                        if tracked_keypoints is None:
                            continue
                        face = Face(
                            bbox=detected_box,
                            kps=tracked_keypoints[detection_index],
                            det_score=float(
                                tracked_detections.confidence[detection_index]
                            ),
                        )
                        embedding_started = time.perf_counter()
                        engine.models["recognition"].get(frame, face)
                        embedding_elapsed = time.perf_counter() - embedding_started
                        stats_embedding += embedding_elapsed
                        stats_embedding_calls += 1
                        log_timing(
                            f"track #{track.track_id} embedding",
                            embedding_elapsed,
                        )
                        track.name = "Qidirilmoqda..."
                        pending_queries[track.track_id] = asyncio.create_task(
                            asyncio.to_thread(
                                search_face_in_qdrant,
                                search_client,
                                face.normed_embedding.tolist(),
                            )
                        )
                    else:
                        track = tracks[byte_track_id]
                        track.bbox = box
                        track.last_seen = frame_number

                tracks = {
                    track_id: track
                    for track_id, track in tracks.items()
                    if frame_number - track.last_seen <= TRACK_MAX_MISSING_FRAMES
                }

            for track in tracks.values():
                x1, y1, x2, y2 = (int(value) for value in track.bbox)
                label = f"#{track.track_id} {track.name}"
                if track.score is not None:
                    label += f" {track.score:.2f}"
                color = (0, 220, 0) if track.recognized else (0, 220, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    label,
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                    cv2.LINE_AA,
                )

            cv2.imshow("Face recognition (CPU) - Q to exit", frame)
            should_quit = cv2.waitKey(1) & 0xFF == ord("q")
            # Let background HTTP tasks make progress without freezing video.
            await asyncio.sleep(0.001)
            stats_loop += time.perf_counter() - loop_started
            if stats_frames >= TIMING_LOG_EVERY_N_FRAMES:
                elapsed = time.perf_counter() - stats_started
                divisor = stats_frames or 1
                print(
                    f"[vaqt, oxirgi {stats_frames} kadr] "
                    f"kamera={stats_read / divisor * 1000:.1f} ms/kadr, "
                    f"detection={stats_detection * 1000:.1f} ms jami/"
                    f"{stats_detection_calls} chaqiruv "
                    f"({stats_detection * 1000 / max(1, stats_detection_calls):.1f} ms/chaqiruv), "
                    f"embedding={stats_embedding * 1000:.1f} ms jami/"
                    f"{stats_embedding_calls} yangi track, "
                    f"ByteTrack={stats_tracking * 1000:.1f} ms jami, "
                    f"Qdrant={stats_qdrant * 1000:.1f} ms jami, "
                    f"sikl={stats_loop * 1000 / divisor:.1f} ms/kadr, "
                    f"FPS={stats_frames / elapsed:.1f}",
                    flush=True,
                )
                stats_started = time.perf_counter()
                stats_frames = 0
                stats_read = stats_detection = stats_embedding = 0.0
                stats_tracking = 0.0
                stats_qdrant = stats_loop = 0.0
                stats_detection_calls = stats_embedding_calls = 0
            if should_quit:
                break
    finally:
        if pending_queries:
            await asyncio.gather(
                *pending_queries.values(),
                return_exceptions=True,
            )
        camera.release()
        cv2.destroyAllWindows()
        search_client.close()
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Face enrollment and recognition")
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser("register", help="User yuzini Qdrant'ga yozish")
    register.add_argument("user_id")
    register.add_argument("full_name")
    register.add_argument("image_path")

    commands.add_parser("camera", help="Kameradan real vaqtda yuzni tanish")
    args = parser.parse_args()

    if args.command == "register":
        asyncio.run(register_user(args.user_id, args.full_name, args.image_path))
    else:
        asyncio.run(recognize_camera())


if __name__ == "__main__":
    main()
