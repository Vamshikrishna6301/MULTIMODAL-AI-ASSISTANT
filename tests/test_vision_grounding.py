from core.response_model import UnifiedResponse
from execution.vision.element_selector import ElementSelector
from execution.vision.screen_element import ScreenElement
from execution.vision.vision_executor import VisionExecutor


def test_element_selector_prefers_matching_color_and_type():
    selector = ElementSelector()
    elements = [
        ScreenElement(
            element_id=1,
            name="settings",
            element_type="icon",
            bbox=(0, 0, 40, 40),
            confidence=0.7,
            source="VISION",
            attributes={"dominant_color": "blue", "semantic_role": "icon"},
        ),
        ScreenElement(
            element_id=2,
            name="notifications",
            element_type="icon",
            bbox=(50, 0, 90, 40),
            confidence=0.7,
            source="VISION",
            attributes={"dominant_color": "red", "semantic_role": "icon"},
        ),
    ]

    selected = selector.select_best("red icon", elements)

    assert selected is not None
    assert selected.name == "notifications"


def test_element_selector_prefers_text_match_for_login_button():
    selector = ElementSelector()
    elements = [
        ScreenElement(
            element_id=1,
            name="signup",
            element_type="button",
            bbox=(0, 0, 120, 40),
            confidence=0.9,
            source="UIA",
            attributes={"semantic_role": "button"},
        ),
        ScreenElement(
            element_id=2,
            name="login",
            element_type="button",
            bbox=(0, 50, 120, 90),
            confidence=0.8,
            source="OCR",
            attributes={"semantic_role": "button"},
        ),
    ]

    selected = selector.select_best("login button", elements)

    assert selected is not None
    assert selected.name == "login"


class _FakeCapture:
    def capture(self):
        import numpy as np

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:50, 10:50] = (0, 0, 255)
        return frame


class _FakeOCR:
    def extract_elements(self, frame):
        return [{"text": "login", "bbox": (10, 10, 50, 40), "confidence": 0.95}]


class _FakeUIDetector:
    def detect(self, frame):
        return [{"text": "icon", "bbox": (10, 10, 50, 50), "confidence": 0.8, "element_type": "icon", "semantic_role": "icon"}]


class _FakeUIA:
    def read_screen(self):
        return {"status": "success", "elements": []}


class _FakeClickEngine:
    def __init__(self):
        self.clicked = None

    def click(self, element):
        self.clicked = element
        return True


def test_vision_executor_clicks_grounded_query():
    executor = VisionExecutor()
    executor.screen_capture = _FakeCapture()
    executor.ocr_engine = _FakeOCR()
    executor.ui_detector = _FakeUIDetector()
    executor.uia_client = _FakeUIA()
    executor.click_engine = _FakeClickEngine()

    response = executor.handle(
        {
            "action": "VISION",
            "target": "screen",
            "parameters": {"task": "click", "query": "login button"},
        }
    )

    assert response.success is True
    assert response.metadata["selected_element"]["name"] == "login"
    assert executor.click_engine.clicked.name == "login"
