"""
Phase 4 — Vision Integration
Advanced vision mode controller with screen reading, object detection, and scene understanding
"""


class VisionMode:
    """Vision operation modes for assistive AI"""
    
    SILENT = "SILENT"          # No automatic narration
    PASSIVE = "PASSIVE"        # Only announce person entry/exit
    ALERT = "ALERT"            # Announce motion, obstacles
    SAFETY = "SAFETY"          # Fire/smoke, fall detection


class VisionModeController:
    """
    Controls vision system behavior based on user preference
    Manages what gets announced and when
    """
    
    def __init__(self):
        self.current_mode = VisionMode.SILENT
        self.mode_callbacks = {
            VisionMode.SILENT: self._handle_silent,
            VisionMode.PASSIVE: self._handle_passive,
            VisionMode.ALERT: self._handle_alert,
            VisionMode.SAFETY: self._handle_safety,
        }
    
    def set_mode(self, mode: str):
        """Switch vision mode"""
        if mode not in self.mode_callbacks:
            raise ValueError(f"Unknown vision mode: {mode}")
        self.current_mode = mode
        print(f"📷 Vision mode: {mode}")
    
    def process_event(self, event: dict, tts=None):
        """Process vision event based on current mode"""
        handler = self.mode_callbacks.get(self.current_mode)
        if handler:
            handler(event, tts)
    
    def _handle_silent(self, event: dict, tts=None):
        """Silent mode: no announcements"""
        pass
    
    def _handle_passive(self, event: dict, tts=None):
        """Passive mode: only announce person entry"""
        event_type = event.get("type")
        if event_type in ["person_entered", "person_exited"] and tts:
            msg = "A person has entered" if event_type == "person_entered" else "A person has left"
            tts.speak(msg)
    
    def _handle_alert(self, event: dict, tts=None):
        """Alert mode: announce motion and obstacles"""
        event_type = event.get("type")
        if tts:
            if event_type == "motion_detected":
                tts.speak("Motion detected")
            elif event_type == "obstacle_detected":
                msg = event.get("message", "Obstacle ahead")
                tts.speak(msg)
            elif "person" in event_type:
                msg = "A person has " + ("entered" if "entered" in event_type else "left")
                tts.speak(msg)
    
    def _handle_safety(self, event: dict, tts=None):
        """Safety mode: announce critical threats"""
        event_type = event.get("type")
        if tts:
            if "fire" in event_type or "smoke" in event_type:
                tts.speak("ALERT: Potential fire detected!")
            elif "fall" in event_type:
                tts.speak("ALERT: Fall detected!")
            elif "door_opened" in event_type:
                tts.speak("Door opened")
