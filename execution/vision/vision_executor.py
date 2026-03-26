from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.response_model import UnifiedResponse
from execution.uia_service.uia_client import UIAClient
from execution.vision.camera_detector import CameraDetector
from execution.vision.click_engine import ClickEngine
from execution.vision.element_selector import ElementSelector
from execution.vision.layout_analyzer import LayoutAnalyzer
from execution.vision.ocr_engine import OCREngine
from execution.vision.screen_capture import ScreenCapture
from execution.vision.screen_element import ScreenElement
from execution.vision.screen_element_graph import ScreenElementGraph
from execution.vision.scene_reasoner import SceneReasoner
from execution.vision.scene_graph_engine import SceneGraphEngine
from execution.vision.screen_monitoring_engine import ScreenMonitoringEngine
from execution.vision.stabilization_buffer import StabilizationBuffer
from execution.vision.ui_detector import UIDetector
from execution.vision.vision_mode_controller import VisionModeController


class VisionExecutor:

    COLOR_RANGES = {
        "red": [((0, 80, 80), (12, 255, 255)), ((165, 80, 80), (180, 255, 255))],
        "green": [((35, 60, 60), (85, 255, 255))],
        "blue": [((90, 60, 60), (135, 255, 255))],
        "yellow": [((20, 80, 80), (35, 255, 255))],
        "orange": [((10, 80, 80), (20, 255, 255))],
        "purple": [((135, 60, 60), (165, 255, 255))],
        "pink": [((145, 40, 80), (175, 255, 255))],
        "white": [((0, 0, 180), (180, 45, 255))],
        "black": [((0, 0, 0), (180, 255, 45))],
        "gray": [((0, 0, 46), (180, 30, 179))],
    }

    def __init__(self):

        self.screen_capture = ScreenCapture()
        self.ocr_engine = OCREngine()
        self.camera_detector = CameraDetector()
        self.scene_graph = SceneGraphEngine()
        self.stabilization = StabilizationBuffer()
        self.screen_monitor = ScreenMonitoringEngine()
        self.vision_mode = VisionModeController()
        self.element_graph = ScreenElementGraph()
        self.selector = ElementSelector()
        self.uia_client = UIAClient()
        self.click_engine = ClickEngine(self.uia_client)
        self.layout_analyzer = LayoutAnalyzer()
        self.ui_detector = UIDetector()
        self.scene_reasoner = SceneReasoner()
        self._tts = None

    def set_tts(self, tts):
        self._tts = tts
        self.camera_detector.tts = tts

    def handle(self, decision: dict) -> UnifiedResponse:

        try:
            action = decision.get("action")
            target = decision.get("target", "")
            parameters = decision.get("parameters", {}) or {}
            task = parameters.get("task") or decision.get("task") or "describe"

            if action == "START_SCENE_UNDERSTANDING":
                return self._handle_camera("start")

            if action == "STOP_SCENE_UNDERSTANDING":
                return self._handle_camera("stop")

            if action == "QUERY_OBJECT":
                return self._handle_query_object(parameters.get("object") or target or "")

            if target == "camera":
                return self._handle_camera(task)

            if target != "screen":
                return UnifiedResponse.error_response(
                    category="vision",
                    spoken_message="Invalid vision target.",
                    error_code="VISION_INVALID_TARGET"
                )

            frame = self.screen_capture.capture()
            elements = self._build_screen_element_graph(frame)
            _ = self.layout_analyzer.analyze(elements)

            if task == "read_text":
                return self._handle_read_text(elements)

            if task == "monitor_screen":
                return self._handle_monitor_screen()

            if task == "click":
                query = parameters.get("query") or decision.get("target_query") or ""
                return self._handle_click_query(query, elements)

            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=self._describe_screen(elements),
                metadata={"element_count": len(elements)}
            )

        except Exception as exc:
            return UnifiedResponse.error_response(
                category="vision",
                spoken_message="Vision processing failed.",
                error_code="VISION_ERROR",
                technical_message=str(exc)
            )

    def _handle_camera(self, task: str) -> UnifiedResponse:
        if task == "stop":
            self.camera_detector.stop()
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message="Camera stopped."
            )

        start_message = self.camera_detector.start()
        if start_message:
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=start_message
            )
        start = time.time()
        while time.time() - start < 5:
            detections = self.camera_detector.get_latest_detections()
            if detections:
                break
            time.sleep(0.3)

        detections = self.camera_detector.get_latest_detections()
        normalized = [
            {"name": detection.get("name") or detection.get("label")}
            for detection in detections
            if detection.get("name") or detection.get("label")
        ]
        summary = self.scene_reasoner.describe_scene(normalized)
        return UnifiedResponse.success_response(
            category="vision",
            spoken_message=summary
        )

    def _handle_query_object(self, object_name: str) -> UnifiedResponse:
        memory = getattr(self.camera_detector, "environment_memory", None)
        if memory is None or not object_name:
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message="I cannot locate that object."
            )

        data = memory.query(object_name)
        if not data:
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=f"I cannot locate the {memory._normalize(object_name)}."
            )

        return UnifiedResponse.success_response(
            category="vision",
            spoken_message=f"The {memory._normalize(object_name)} is in front of you."
        )

    def _build_screen_element_graph(self, frame) -> List[ScreenElement]:
        self.element_graph.clear()

        for element in self.ocr_engine.extract_elements(frame):
            self.element_graph.add_element(
                name=element["text"],
                element_type="text",
                bbox=element["bbox"],
                confidence=element["confidence"],
                source="OCR",
                attributes={
                    "ocr_text": element["text"],
                    "semantic_role": "text",
                    "dominant_color": self._dominant_color(frame, element["bbox"]),
                },
            )

        for element in self.ui_detector.detect(frame):
            self.element_graph.add_element(
                name=element["text"],
                element_type=element.get("element_type", "visual"),
                bbox=element["bbox"],
                confidence=element["confidence"],
                source="VISION",
                attributes={
                    "semantic_role": element.get("semantic_role", element.get("element_type", "visual")),
                    "dominant_color": self._dominant_color(frame, element["bbox"]),
                },
            )

        uia_result = self.uia_client.read_screen()
        if isinstance(uia_result, dict) and uia_result.get("status") == "success":
            for element in uia_result.get("elements", []):
                name = (element.get("name") or "").lower().strip()
                if not name:
                    continue
                self.element_graph.add_element(
                    name=name,
                    element_type=(element.get("type") or "uia").lower(),
                    bbox=tuple(element.get("bbox", (0, 0, 0, 0))),
                    confidence=float(element.get("confidence", 0.9)),
                    source="UIA",
                    attributes={
                        "semantic_role": (element.get("type") or "uia").lower(),
                        "dominant_color": element.get("dominant_color", ""),
                    },
                )

        return self.element_graph.get_elements()

    def _handle_read_text(self, elements: List[ScreenElement]) -> UnifiedResponse:
        names = [element.name for element in elements if element.name][:10]
        if not names:
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message="No readable text detected."
            )

        return UnifiedResponse.success_response(
            category="vision",
            spoken_message="I see: " + ", ".join(names),
            metadata={"element_count": len(elements)}
        )

    def _handle_monitor_screen(self) -> UnifiedResponse:
        result = self.screen_monitor.monitor(tts=self._tts)
        msg = "Screen monitoring active"
        if result["keywords_detected"]:
            msg += f": detected {', '.join(result['keywords_detected'])}"
        return UnifiedResponse.success_response(
            category="vision",
            spoken_message=msg
        )

    def _handle_click_query(self, query: str, elements: List[ScreenElement]) -> UnifiedResponse:
        ranked = self.selector.rank(query, elements)
        if not ranked:
            return UnifiedResponse.error_response(
                category="vision",
                spoken_message=f"I cannot find {query or 'that element'} on the screen.",
                error_code="ELEMENT_NOT_FOUND"
            )

        element, score = ranked[0]
        success = self.click_engine.click(element)

        if success:
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=f"Clicked {element.name}.",
                metadata={
                    "grounded_query": query,
                    "selected_element": element.to_dict(),
                    "selection_score": score,
                }
            )

        return UnifiedResponse.error_response(
            category="vision",
            spoken_message="I found the element but could not click it.",
            error_code="CLICK_FAILED",
            metadata={
                "grounded_query": query,
                "selected_element": element.to_dict(),
                "selection_score": score,
            }
        )

    def _describe_screen(self, elements: List[ScreenElement]) -> str:
        if not elements:
            return "No interactive elements detected on the screen."

        top = [element.name for element in elements if element.name][:8]
        if not top:
            return "I captured the screen but could not ground any elements."
        return "I can interact with: " + ", ".join(top)

    def _dominant_color(self, frame, bbox: Tuple[int, int, int, int]) -> str:
        if frame is None:
            return ""

        x1, y1, x2, y2 = bbox
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame.shape[1], max(x1 + 1, x2))
        y2 = min(frame.shape[0], max(y1 + 1, y2))

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return ""

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        best_color = ""
        best_ratio = 0.0

        for color, ranges in self.COLOR_RANGES.items():
            mask_total = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                mask = cv2.inRange(
                    hsv,
                    np.array(lower, dtype=np.uint8),
                    np.array(upper, dtype=np.uint8),
                )
                mask_total = cv2.bitwise_or(mask_total, mask)

            ratio = float(np.count_nonzero(mask_total)) / float(mask_total.size)
            if ratio > best_ratio:
                best_ratio = ratio
                best_color = color

        return best_color if best_ratio >= 0.12 else ""
