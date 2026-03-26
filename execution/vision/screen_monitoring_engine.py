"""
Phase 4 — Screen Monitoring Engine
Detects screen changes and keyword alerts
"""
import cv2
import numpy as np
from execution.vision.screen_capture import ScreenCapture
from execution.vision.ocr_engine import OCREngine


class ScreenMonitoringEngine:
    """
    Monitors screen for:
    - Text changes
    - Keyword alerts
    - Error detection
    - Notification reading
    """
    
    def __init__(self):
        self.screen_capture = ScreenCapture()
        self.ocr_engine = OCREngine()
        self.previous_frame = None
        self.previous_text = ""
        self.keyword_alerts = [
            "error", "warning", "exception", "alert",
            "failed", "invalid", "disconnected", "timeout"
        ]
    
    def read_screen(self) -> str:
        """Read current screen text via OCR"""
        try:
            frame = self.screen_capture.capture()
            text = self.ocr_engine.extract_text(frame)
            return text
        except Exception as e:
            print(f"❌ Screen read failed: {e}")
            return ""
    
    def detect_screen_change(self) -> bool:
        """Detect if screen content changed significantly"""
        try:
            frame = self.screen_capture.capture()
            
            if self.previous_frame is None:
                self.previous_frame = frame
                return False
            
            # Compute difference between frames
            diff = cv2.absdiff(self.previous_frame, frame)
            change_percentage = (np.sum(diff) / diff.size) * 100
            
            self.previous_frame = frame
            
            # Screen changed if >5% of pixels different
            return change_percentage > 5.0
            
        except Exception as e:
            print(f"❌ Screen change detection failed: {e}")
            return False
    
    def detect_keywords(self, text: str) -> list:
        """Detect alert keywords in screen text"""
        alerts = []
        text_lower = text.lower()
        
        for keyword in self.keyword_alerts:
            if keyword in text_lower:
                alerts.append(keyword)
        
        return alerts
    
    def monitor(self, tts=None) -> dict:
        """
        Single monitoring cycle
        
        Returns:
            dict with changes, keywords, text
        """
        current_text = self.read_screen()
        screen_changed = self.detect_screen_change()
        keywords = self.detect_keywords(current_text)
        
        result = {
            "screen_changed": screen_changed,
            "keywords_detected": keywords,
            "current_text": current_text,
            "text_changed": current_text != self.previous_text
        }
        
        # Announce alerts
        if keywords and tts:
            for keyword in keywords:
                tts.speak(f"Alert: {keyword} detected on screen")
        
        self.previous_text = current_text
        return result
    
    def get_region_ocr(self, x, y, width, height) -> str:
        """
        Read OCR from specific screen region
        Useful for reading specific windows or panels
        """
        try:
            frame = self.screen_capture.capture()
            region = frame[y:y+height, x:x+width]
            text = self.ocr_engine.extract_text(region)
            return text
        except Exception as e:
            print(f"❌ Region OCR failed: {e}")
            return ""
