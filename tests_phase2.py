from execution.vision.click_engine import ClickEngine
from execution.vision.screen_element import ScreenElement

engine = ClickEngine()

element = ScreenElement(
    element_id=1,
    name="test_button",
    element_type="text",
    bbox=(500, 500, 600, 550),
    confidence=0.9,
    source="OCR"
)

print("Clicking element center...")

engine.click(element)

print("Click executed.")