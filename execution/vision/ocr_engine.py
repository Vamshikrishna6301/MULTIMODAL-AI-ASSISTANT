from pathlib import Path

import pytesseract
import cv2


TESSERACT_CANDIDATES = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)

for candidate in TESSERACT_CANDIDATES:
    if candidate.exists():
        pytesseract.pytesseract.tesseract_cmd = str(candidate)
        break


class OCREngine:
    """
    Production OCR Engine
    Returns text with bounding boxes for screen interaction
    """

    def extract_text(self, frame):

        if frame is None:
            raise RuntimeError("Invalid frame for OCR")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Improve OCR accuracy
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        text = pytesseract.image_to_string(thresh)

        return text.strip()

    # =====================================================
    # NEW — Extract OCR elements with bounding boxes
    # =====================================================

    def extract_elements(self, frame):

        if frame is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        data = pytesseract.image_to_data(
            gray,
            output_type=pytesseract.Output.DICT
        )

        elements = []

        n = len(data["text"])

        for i in range(n):

            text = data["text"][i].strip()
            conf = float(data["conf"][i])

            if not text:
                continue

            if conf < 50:
                continue

            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            bbox = (x, y, x + w, y + h)

            elements.append({
                "text": text.lower(),
                "bbox": bbox,
                "confidence": conf / 100.0
            })

        return elements
