import os
import threading
import time
from pathlib import Path

import cv2

from config_production import COMPUTE_CONFIG, VISION_CONFIG
from execution.vision.scene_memory import SceneMemory
from execution.vision.tracking_engine import TrackingEngine
from infrastructure.logger import get_logger

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


class CameraDetector:

    def __init__(self, tts=None):
        self.logger = get_logger("vision.camera_detector")

        requested_device = COMPUTE_CONFIG.get("yolo_device", "cuda")
        gpu_available = bool(torch and torch.cuda.is_available())
        self.device = "cuda" if requested_device == "cuda" and gpu_available else "cpu"
        self.model = None
        if YOLO is not None:
            self.model = YOLO(VISION_CONFIG.get("detector_model", "yolov8m.pt"))
            self.model.to(self.device)

        self._running = False
        self._thread = None
        self._capture = None

        self.tts = tts

        self._latest_detections = []
        self._latest_tracked = []
        self._latest_events = []

        self._lock = threading.Lock()
        self._state_lock = threading.Lock()
        self.tracked_objects = {}
        self.last_announced = {}
        self.pending_objects = {}
        self.unstable_labels = {"kite", "donut", "sports ball"}
        self.environment_memory = None

        self.tracker = TrackingEngine()
        self.scene_memory = SceneMemory()

    def start(self):
        with self._state_lock:
            if self._running or (self._thread and self._thread.is_alive()):
                print("Camera already running.")
                return

            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
            )
            self._thread.start()

    def stop(self):
        with self._state_lock:
            running = self._running
            self._running = False
            thread = self._thread

        if not running and not (thread and thread.is_alive()):
            self.tracked_objects = {}
            self.last_announced = {}
            self.pending_objects = {}
            return

        print("Stopping camera...")

        if thread and thread.is_alive():
            thread.join(timeout=2)

        self.tracked_objects = {}
        self.last_announced = {}
        self.pending_objects = {}

    def get_latest_detections(self):
        with self._lock:
            return list(self._latest_detections)

    def get_tracked_objects(self):
        with self._lock:
            return list(self._latest_tracked)

    def get_scene_events(self):
        with self._lock:
            return list(self._latest_events)

    def detect_objects(self):

        self.start()

        start = time.time()
        warmup_grace = 8

        while time.time() - start < warmup_grace:
            detections = self.get_latest_detections()

            if detections:
                return [
                    {"name": d.get("name") or d.get("label", "object")}
                    for d in detections
                    if d.get("name") or d.get("label")
                ]

            time.sleep(0.25)

        return []

    def describe_current_scene(self):

        detections = self.get_latest_detections()

        if not detections:
            return "I do not see anything clearly."

        names = list(dict.fromkeys(
            detection.get("name") or detection.get("label")
            for detection in detections
            if detection.get("name") or detection.get("label")
        ))

        if not names:
            return "I do not see anything clearly."

        return "I can see " + ", ".join(names[:5]) + "."

    def _announce(self, message: str) -> None:
        print(f"[VISION EVENT] {message}")
        self.logger.debug("object_detection_event", event=message)
        if self.tts:
            try:
                self.tts.speak(message)
            except Exception:
                pass

    def _run_loop(self):
        cap = None
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self._capture = cap
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            if not cap.isOpened():
                print("Unable to access camera.")
                return

            if self.model is None:
                print("Ultralytics model unavailable.")
                return

            print("Camera started.")

            frame_skip = 0

            while self._running:

                ret, frame = cap.read()
                if not ret:
                    break

                frame_skip += 1

                if frame_skip % 3 != 0:
                    cv2.imshow("Assistant Camera", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                results = self.model.predict(
                    source=frame,
                    device=self.device,
                    conf=VISION_CONFIG.get("detection_confidence", 0.3),
                    verbose=False,
                )

                detections = []

                for result in results:
                    for box in result.boxes:

                        confidence = float(box.conf[0])
                        if confidence < 0.6:
                            continue

                        class_id = int(box.cls[0])
                        class_name = self.model.names[class_id]
                        if class_name in self.unstable_labels and confidence < 0.65:
                            continue
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        detections.append({
                            "name": class_name,
                            "label": class_name,
                            "confidence": confidence,
                            "bbox": (x1, y1, x2, y2),
                        })

                        label = f"{class_name} {confidence:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(
                            frame,
                            label,
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 0),
                            2,
                        )

                tracked_objects = self.tracker.update(detections)
                events = self.scene_memory.update(tracked_objects)

                announcements = []
                now = time.time()
                current_labels = set()

                for detection in detections:
                    label = detection.get("name") or detection.get("label")
                    bbox = detection.get("bbox")
                    if not label:
                        continue
                    current_labels.add(label)
                    pending_count = self.pending_objects.get(label, 0) + 1
                    self.pending_objects[label] = pending_count
                    tracked = self.tracked_objects.get(label)
                    if tracked is None:
                        self.tracked_objects[label] = {
                            "last_seen_time": now,
                            "last_position": bbox,
                        }
                        if pending_count < 2:
                            continue
                        last = self.last_announced.get(label, 0)
                        if now - last > 8:
                            announcements.append(f"A {label} entered the scene.")
                            self.last_announced[label] = now
                        continue
                    tracked["last_seen_time"] = now
                    tracked["last_position"] = bbox

                for label, tracked in list(self.tracked_objects.items()):
                    if label in current_labels:
                        continue
                    self.pending_objects.pop(label, None)
                    if now - tracked["last_seen_time"] > 2:
                        announcements.append(f"The {label} left the scene.")
                        del self.tracked_objects[label]

                for message in announcements:
                    self._announce(message)

                with self._lock:
                    self._latest_detections = detections
                    self._latest_tracked = tracked_objects
                    self._latest_events = list(events) + announcements

                if self.environment_memory is not None:
                    try:
                        self.environment_memory.update_objects(detections)
                    except Exception:
                        pass

                cv2.imshow("Assistant Camera", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        except Exception as e:
            self.logger.error("camera_loop_error", error=str(e))
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            cv2.destroyAllWindows()
            with self._state_lock:
                self._running = False
                self._capture = None
                self._thread = None
            self.tracked_objects = {}
            self.pending_objects = {}
            print("Camera stopped.")
