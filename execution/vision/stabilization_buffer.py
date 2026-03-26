"""
Vision Stabilization Buffer
Prevents flickering detections and false positives
"""
from collections import deque
import time


class StabilizationBuffer:
    """
    Smooths vision data to prevent:
    - Objects flickering in/out of view
    - Counting errors from detection jitter
    - False motion alerts
    """
    
    def __init__(self, buffer_size: int = 5, min_duration: float = 1.0):
        """
        Args:
            buffer_size: Number of frames to keep in history
            min_duration: Minimum seconds before confirming presence
        """
        self.buffer_size = buffer_size
        self.min_duration = min_duration
        self.detection_buffer = deque(maxlen=buffer_size)
        self.object_timestamps = {}  # Track when objects first appeared
    
    def add_detections(self, detections: list) -> list:
        """
        Add new detections and return stabilized version
        
        Args:
            detections: List of detected objects with labels, confidence, etc
            
        Returns:
            Stabilized detections (may be from previous frame if unstable)
        """
        current_time = time.time()
        self.detection_buffer.append({
            'detections': detections,
            'timestamp': current_time
        })
        
        # Update object lifetime tracking
        detected_labels = set(d.get('label') for d in detections)
        for label in detected_labels:
            if label not in self.object_timestamps:
                self.object_timestamps[label] = current_time
        
        # Remove objects that disappeared
        for label in list(self.object_timestamps.keys()):
            if label not in detected_labels:
                del self.object_timestamps[label]
        
        # Return stabilized detections
        if len(self.detection_buffer) < 2:
            return detections
        
        return self._stabilize()
    
    def _stabilize(self) -> list:
        """Apply stabilization logic"""
        if len(self.detection_buffer) == 0:
            return []
        
        # Get most recent entry
        recent = self.detection_buffer[-1]
        detections = recent['detections']
        
        # Filter by minimum confidence
        stable_detections = []
        for det in detections:
            confidence = det.get('confidence', 0.0)
            if confidence >= 0.5:  # Confidence threshold
                # Check if object appeared long enough
                label = det.get('label')
                first_seen = self.object_timestamps.get(label, time.time())
                duration = time.time() - first_seen
                
                if duration >= self.min_duration or len(self.detection_buffer) > 3:
                    stable_detections.append(det)
        
        return stable_detections
    
    def get_stable_count(self, label: str) -> int:
        """
        Get stabilized count of specific object
        
        Args:
            label: Object label (e.g., 'person', 'phone')
            
        Returns:
            Stable count across buffer
        """
        if len(self.detection_buffer) < 2:
            return 0
        
        counts = []
        current_time = time.time()
        
        for entry in self.detection_buffer:
            detections = entry['detections']
            count = sum(1 for d in detections 
                       if d.get('label') == label 
                       and d.get('confidence', 0) >= 0.5)
            counts.append(count)
        
        # Return most common count (mode)
        if counts:
            return max(set(counts), key=counts.count)
        return 0
    
    def detect_entry_exit(self, label: str, threshold: int = 1) -> str:
        """
        Detect if objects entered or exited
        
        Args:
            label: Object label to track
            threshold: Minimum count change to register as entry/exit
            
        Returns:
            'entered', 'exited', or 'none'
        """
        if len(self.detection_buffer) < 2:
            return 'none'
        
        # Compare first and last entries
        first_entry = self.detection_buffer[0]
        last_entry = self.detection_buffer[-1]
        
        first_count = sum(1 for d in first_entry['detections'] 
                         if d.get('label') == label)
        last_count = sum(1 for d in last_entry['detections'] 
                        if d.get('label') == label)
        
        if last_count > first_count and last_count - first_count >= threshold:
            return 'entered'
        elif first_count > last_count and first_count - last_count >= threshold:
            return 'exited'
        
        return 'none'
    
    def reset(self):
        """Clear buffer"""
        self.detection_buffer.clear()
        self.object_timestamps.clear()
