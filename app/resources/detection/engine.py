import logging
import threading
import typing as t
import zipfile
from pathlib import Path

import numpy as np
from insightface.app import FaceAnalysis
from insightface.app.common import Face

from config.settings import APP_SETTINGS

logger = logging.getLogger(__name__)

_engine: FaceAnalysis | None = None
_engine_init_lock = threading.Lock()
inference_lock = threading.Lock()


def _extract_model_archive(model_name: str) -> None:
    models_root = Path.home() / '.insightface' / 'models'
    model_directory = models_root / model_name
    if model_directory.exists() and any(model_directory.glob('*.onnx')):
        return

    archive_path = models_root / f'{model_name}.zip'
    if not archive_path.is_file():
        return

    models_root.mkdir(parents=True, exist_ok=True)
    root = models_root.resolve()
    logger.info('Extracting InsightFace model archive: %s', archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            destination = (models_root / member.filename).resolve()
            if destination != root and root not in destination.parents:
                raise RuntimeError(
                    f'Unsafe path in model archive {archive_path}: {member.filename}'
                )
        archive.extractall(models_root)

    if not model_directory.exists() or not any(model_directory.glob('*.onnx')):
        raise RuntimeError(
            f'Model archive {archive_path} does not contain {model_name} ONNX files'
        )


def get_face_engine() -> FaceAnalysis:
    global _engine
    if _engine is None:
        with _engine_init_lock:
            if _engine is None:
                model_name = APP_SETTINGS.MODEL_NAME
                _extract_model_archive(model_name)
                try:
                    engine = FaceAnalysis(
                        name=model_name,
                        allowed_modules=['detection', 'recognition'],
                        providers=['CPUExecutionProvider'],
                    )
                except AssertionError as exc:
                    model_directory = Path.home() / '.insightface' / 'models' / model_name
                    raise RuntimeError(
                        f'InsightFace model "{model_name}" has no usable detection model '
                        f'in {model_directory}'
                    ) from exc
                engine.prepare(
                    ctx_id=-1,
                    det_thresh=0.25,
                    det_size=APP_SETTINGS.DETECTION_SIZE,
                )
                _engine = engine
    return _engine


def analyze_face_image(image: np.ndarray) -> t.List[Face]:
    engine = get_face_engine()
    with inference_lock:
        return engine.get(image)
