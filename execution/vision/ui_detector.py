from __future__ import annotations

import os
from pathlib import Path
from typing import List

import cv2

from config_production import COMPUTE_CONFIG, VISION_CONFIG

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ULTRALYTICS_DIR = _PROJECT_ROOT / ".cache" / "ultralytics"
_ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_ULTRALYTICS_DIR))
os.environ.setdefault("ULTRALYTICS_CONFIG_DIR", str(_ULTRALYTICS_DIR))

try:
    import torch  # type: ignore
except ImportError:  # pragma: no cover - optional at runtime
    torch = None

try:
    from ultralytics import YOLO  # type: ignore
except ImportError:  # pragma: no cover - optional at runtime
    YOLO = None


class UIDetector:
    """
    Screen UI detector that prefers Ultralytics YOLO on GPU and falls back to
    simple contour-based detection when the model stack is unavailable.
    """

    _shared_model = None
    _shared_model_path = None
    _shared_device = None

    def __init__(self):
        self.model_path = VISION_CONFIG.get("detector_model", "yolov8n.pt")
        requested_device = COMPUTE_CONFIG.get("yolo_device", "cuda")
        gpu_available = bool(torch and torch.cuda.is_available())
        self.device = "cuda" if requested_device == "cuda" and gpu_available else "cpu"
        self.confidence_threshold = float(VISION_CONFIG.get("detection_confidence", 0.3))
        self.model = self._get_model()

    def detect(self, frame) -> List[dict]:
        if frame is None:
            return []

        if self.model is not None:
            try:
                return self._detect_with_yolo(frame)
            except Exception:
                pass

        return self._detect_with_contours(frame)

    def _get_model(self):
        if YOLO is None:
            return None

        if (
            UIDetector._shared_model is not None
            and UIDetector._shared_model_path == self.model_path
            and UIDetector._shared_device == self.device
        ):
            return UIDetector._shared_model

        model = YOLO(self.model_path)
        try:
            model.to(self.device)
        except Exception:
            self.device = "cpu"
            model.to(self.device)

        UIDetector._shared_model = model
        UIDetector._shared_model_path = self.model_path
        UIDetector._shared_device = self.device
        return model

    def _detect_with_yolo(self, frame) -> List[dict]:
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            device=self.device,
            verbose=False,
        )

        detections: List[dict] = []
        for result in results:
            names = getattr(result, "names", {}) or {}
            for box in getattr(result, "boxes", []):
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                label = str(names.get(class_id, f"class_{class_id}")).lower()
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(
                    {
                        "text": label,
                        "bbox": (x1, y1, x2, y2),
                        "confidence": confidence,
                        "element_type": self._element_type_for_label(label),
                        "semantic_role": self._element_type_for_label(label),
                    }
                )
        return detections

    def _detect_with_contours(self, frame) -> List[dict]:
        detections = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 30 or h < 20:
                continue
            if w > 300 or h > 200:
                continue

            detections.append(
                {
                    "text": "visual_button",
                    "bbox": (x, y, x + w, y + h),
                    "confidence": 0.6,
                    "element_type": "button",
                    "semantic_role": "button",
                }
            )

        return detections

    def _element_type_for_label(self, label: str) -> str:
        if label in {"button", "cell phone", "keyboard", "laptop", "remote", "mouse"}:
            return "button"
        if label in {"tv", "monitor"}:
            return "panel"
        if label in {"book", "person"}:
            return "visual"
        return "icon"
