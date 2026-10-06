import threading

from aiortc import RTCPeerConnection
from insightface.app import FaceAnalysis

from config.settings import APP_SETTINGS

_engine: FaceAnalysis | None = None
_engine_init_lock = threading.Lock()
_inference_lock = threading.Lock()
_peer_connections: set[RTCPeerConnection] = set()


def get_face_engine() -> FaceAnalysis:
    global _engine
    if _engine is None:
        with _engine_init_lock:
            if _engine is None:
                engine = FaceAnalysis(
                    name=APP_SETTINGS.MODEL_NAME,
                    allowed_modules=['detection', 'recognition'],
                    providers=['CPUExecutionProvider'],
                )
                engine.prepare(
                    ctx_id=-1,
                    det_thresh=0.25,
                    det_size=APP_SETTINGS.DETECTION_SIZE,
                )
                _engine = engine
    return _engine
