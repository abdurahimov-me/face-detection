import asyncio
import os
from dataclasses import dataclass

import cv2
import numpy as np
import onnxruntime as ort

from insightface.app import FaceAnalysis
from qdrant_client import AsyncQdrantClient


# =========================================================
# CONFIG
# =========================================================

INPUT_VIDEO = "input.mp4"
OUTPUT_VIDEO = "output.mp4"

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "faces"

# cpu | cuda | auto
DEVICE = os.getenv("DEVICE", "auto")

# CPU uchun 320/480 ham sinab ko'rish mumkin
DET_SIZE = (640, 640)

# Buni dataset bilan calibrate qilish kerak.
FACE_THRESHOLD = 0.55

# Detectionlarni bir track deb hisoblash uchun
IOU_THRESHOLD = 0.30

# Track qancha frame ko'rinmasa o'chiriladi
MAX_MISSING_FRAMES = 15


# =========================================================
# INSIGHTFACE
# =========================================================

def create_face_engine() -> FaceAnalysis:
    available = ort.get_available_providers()

    print("Available ONNX providers:", available)

    if DEVICE == "cpu":
        providers = [
            "CPUExecutionProvider",
        ]
        ctx_id = -1

    elif DEVICE == "cuda":
        if "CUDAExecutionProvider" not in available:
            raise RuntimeError(
                "DEVICE=cuda, lekin CUDAExecutionProvider topilmadi"
            )

        providers = [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        ctx_id = 0

    else:
        # auto
        if "CUDAExecutionProvider" in available:
            providers = [
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ]
            ctx_id = 0
        else:
            providers = [
                "CPUExecutionProvider",
            ]
            ctx_id = -1

    print("Using:", providers)

    app = FaceAnalysis(
        name="buffalo_l",
        providers=providers,
    )

    app.prepare(
        ctx_id=ctx_id,
        det_size=DET_SIZE,
    )

    return app


# =========================================================
# SIMPLE TRACKER
#
# Hozir sample uchun IoU tracker.
# Productionda keyinchalik ByteTrack/BoT-SORTga almashtiramiz.
# =========================================================

@dataclass
class Track:
    track_id: int
    bbox: np.ndarray

    full_name: str | None = None
    score: float | None = None

    # Qdrantdan qidirilganmi?
    recognized: bool = False

    # Oxirgi marta qaysi frameda ko'rildi
    last_seen: int = 0


tracks: dict[int, Track] = {}
next_track_id = 1


def calculate_iou(box1, box2) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection_w = max(0, x2 - x1)
    intersection_h = max(0, y2 - y1)

    intersection = intersection_w * intersection_h

    area1 = max(0, box1[2] - box1[0]) * max(
        0,
        box1[3] - box1[1],
    )

    area2 = max(0, box2[2] - box2[0]) * max(
        0,
        box2[3] - box2[1],
    )

    union = area1 + area2 - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def find_track(
    bbox: np.ndarray,
) -> Track | None:

    best_track = None
    best_iou = 0.0

    for track in tracks.values():

        iou = calculate_iou(
            bbox,
            track.bbox,
        )

        if (
            iou >= IOU_THRESHOLD
            and iou > best_iou
        ):
            best_iou = iou
            best_track = track

    return best_track


# =========================================================
# QDRANT
# =========================================================

qdrant = AsyncQdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    timeout=5,
)


async def recognize_face(
    embedding: np.ndarray,
):
    """
    512-d InsightFace embedding ->
    Qdrant ->
    full_name
    """

    response = await qdrant.query_points(
        collection_name=QDRANT_COLLECTION,

        query=embedding.tolist(),

        limit=1,

        score_threshold=FACE_THRESHOLD,

        with_payload=True,

        with_vectors=False,
    )

    if not response.points:
        return None

    point = response.points[0]

    payload = point.payload or {}

    return {
        "full_name": payload.get(
            "full_name",
            "Unknown",
        ),
        "score": float(point.score),
    }


# =========================================================
# DRAW
# =========================================================

def draw_track(
    frame: np.ndarray,
    track: Track,
):
    x1, y1, x2, y2 = track.bbox.astype(int)

    if track.full_name:
        label = track.full_name

        if track.score is not None:
            label += f" {track.score:.2f}"

    else:
        label = "Unknown"

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2,
    )

    cv2.putText(
        frame,
        label,
        (
            x1,
            max(25, y1 - 10),
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )


# =========================================================
# MAIN VIDEO LOOP
# =========================================================

async def main():
    global next_track_id

    face_engine = create_face_engine()

    cap = cv2.VideoCapture(INPUT_VIDEO)

    if not cap.isOpened():
        raise RuntimeError(
            f"Video ochilmadi: {INPUT_VIDEO}"
        )

    fps = cap.get(cv2.CAP_PROP_FPS)

    if not fps or fps <= 0:
        fps = 25

    width = int(
        cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    total_frames = int(
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
    )

    print(
        f"Video: {width}x{height}, "
        f"{fps:.2f} FPS, "
        f"{total_frames} frames"
    )

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    writer = cv2.VideoWriter(
        OUTPUT_VIDEO,
        fourcc,
        fps,
        (width, height),
    )

    frame_number = 0

    try:

        while True:

            success, frame = cap.read()

            if not success:
                break

            frame_number += 1

            # =============================================
            # 1. SCRFD + ArcFace
            #
            # face.bbox
            #     -> SCRFD
            #
            # face.normed_embedding
            #     -> ArcFace
            # =============================================

            detected_faces = face_engine.get(
                frame
            )

            active_track_ids = set()

            for face in detected_faces:

                bbox = face.bbox.astype(
                    np.float32
                )

                embedding = (
                    face.normed_embedding
                )

                if embedding is None:
                    continue

                # =========================================
                # 2. Bu oldingi yuzmi?
                # =========================================

                track = find_track(bbox)

                if track is None:

                    # Yangi yuz
                    track = Track(
                        track_id=next_track_id,
                        bbox=bbox,
                        last_seen=frame_number,
                    )

                    tracks[next_track_id] = track

                    print(
                        "New track:",
                        next_track_id,
                    )

                    next_track_id += 1

                else:

                    track.bbox = bbox
                    track.last_seen = (
                        frame_number
                    )

                active_track_ids.add(
                    track.track_id
                )

                # =========================================
                # 3. Faqat yangi track bo'lsa Qdrant
                # =========================================

                if not track.recognized:

                    result = await recognize_face(
                        embedding
                    )

                    if result is None:

                        track.full_name = (
                            "Unknown"
                        )

                    else:

                        track.full_name = result[
                            "full_name"
                        ]

                        track.score = result[
                            "score"
                        ]

                    track.recognized = True

                    print(
                        f"Track {track.track_id}: "
                        f"{track.full_name} "
                        f"{track.score}"
                    )

                # =========================================
                # 4. Ismni videoga chizish
                # =========================================

                draw_track(
                    frame,
                    track,
                )

            # =============================================
            # 5. Yo'qolib ketgan tracklarni o'chirish
            # =============================================

            expired = []

            for track_id, track in tracks.items():

                missing = (
                    frame_number
                    - track.last_seen
                )

                if missing > MAX_MISSING_FRAMES:
                    expired.append(track_id)

            for track_id in expired:

                del tracks[track_id]

            # =============================================
            # OUTPUT VIDEO
            # =============================================

            writer.write(frame)

            # Real-time oynada ko'rsatish
            cv2.imshow(
                "Face Recognition",
                frame,
            )

            if (
                cv2.waitKey(1) & 0xFF
            ) == ord("q"):
                break

            if frame_number % 100 == 0:
                print(
                    f"{frame_number}/"
                    f"{total_frames}"
                )

    finally:

        cap.release()
        writer.release()

        cv2.destroyAllWindows()

        await qdrant.close()

    print(
        "Done:",
        OUTPUT_VIDEO,
    )


if __name__ == "__main__":
    asyncio.run(main())
