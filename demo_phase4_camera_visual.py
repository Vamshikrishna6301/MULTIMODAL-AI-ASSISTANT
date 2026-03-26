#!/usr/bin/env python3
"""
PHASE 4 — LIVE CAMERA VISUAL DEMONSTRATION
Demonstrates real-time object detection, scene understanding, and visual feedback
"""

import cv2
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.vision.camera_detector import CameraDetector
from execution.vision.scene_graph_engine import SceneGraphEngine
from execution.vision.stabilization_buffer import StabilizationBuffer
from execution.vision.screen_monitoring_engine import ScreenMonitoringEngine


class CameraVisualDemo:
    """Live camera demonstrator with object detection and scene understanding"""
    
    def __init__(self):
        """Initialize camera and vision components"""
        self.detector = CameraDetector()
        self.scene_graph = SceneGraphEngine()
        self.stabilization = StabilizationBuffer(buffer_size=5, min_duration=0.5)
        self.screen_monitor = ScreenMonitoringEngine()
        
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("❌ Camera not available")
            raise RuntimeError("Cannot open camera")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.fps = 30
        self.frame_count = 0
        print("✅ Camera initialized")
        print("Press 'q' to quit, 's' for screenshot, 'space' to pause")

    def draw_detection_box(self, frame, x1, y1, x2, y2, label, conf):
        """Draw bounding box with label"""
        color = (0, 255, 0) if conf > 0.6 else (0, 165, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        text = f"{label} {conf:.2f}"
        cv2.putText(frame, text, (x1, y1 - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def draw_scene_info(self, frame, scene_data):
        """Draw scene understanding information on frame"""
        y_offset = 30
        h, w = frame.shape[:2]
        
        # Semi-transparent background for text
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (w-10, y_offset * 8), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        
        # Draw scene description
        text_color = (0, 255, 0)
        if scene_data.get("description"):
            lines = scene_data["description"].split(".")[:2]  # First 2 sentences
            for i, line in enumerate(lines):
                cv2.putText(frame, line.strip(), (20, y_offset * (i+1)),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)

    def draw_relationships(self, frame, scene_data):
        """Draw relationship information"""
        if not scene_data.get("relationships"):
            return
        
        h, w = frame.shape[:2]
        y_pos = h - 80
        cv2.putText(frame, "RELATIONSHIPS:", (20, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        for i, rel in enumerate(scene_data["relationships"][:3]):
            cv2.putText(frame, f"• {rel}", (30, y_pos + 25 + (i*20)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    def draw_statistics(self, frame, fps, obj_count, stable_count):
        """Draw performance statistics"""
        stats = [
            f"FPS: {fps:.1f}",
            f"Objects: {obj_count}",
            f"Stable: {stable_count}"
        ]
        
        h, w = frame.shape[:2]
        for i, stat in enumerate(stats):
            cv2.putText(frame, stat, (w - 200, 30 + i*25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    def run(self):
        """Run live camera demonstration"""
        print("\n" + "="*60)
        print("🎥 PHASE 4 — LIVE CAMERA VISUAL DEMONSTRATION")
        print("="*60)
        print("\nInitializing components...")
        
        import time
        prev_time = time.time()
        frame_times = []
        paused = False
        last_frame = None
        
        while True:
            if not paused:
                ret, frame = self.cap.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                last_frame = frame.copy()
                self.frame_count += 1
                
                # Detect objects
                detections = self.detector.detect(frame)
                
                # Add to stabilization buffer
                self.stabilization.add_detections(detections)
                stable_count = self.stabilization.get_stable_count()
                
                # Analyze scene with stabilized detections
                stable_detections = []
                if hasattr(self.stabilization, 'buffer') and self.stabilization.buffer:
                    latest = self.stabilization.buffer[-1] if self.stabilization.buffer else []
                    stable_detections = latest
                
                # Draw detections on frame
                for det in detections:
                    x1, y1, x2, y2 = det["bbox"]
                    h, w = frame.shape[:2]
                    x1, y1 = int(x1 * w), int(y1 * h)
                    x2, y2 = int(x2 * w), int(y2 * h)
                    
                    self.draw_detection_box(
                        frame, x1, y1, x2, y2,
                        det["label"], det["confidence"]
                    )
                
                # Generate scene understanding
                if detections:
                    scene_data = self.scene_graph.analyze_frame(detections, frame)
                    self.draw_scene_info(frame, scene_data)
                    self.draw_relationships(frame, scene_data)
                
                # Draw statistics
                current_time = time.time()
                frame_time = current_time - prev_time
                frame_times.append(frame_time)
                if len(frame_times) > 30:
                    frame_times.pop(0)
                
                avg_fps = len(frame_times) / sum(frame_times) if frame_times else 0
                self.draw_statistics(frame, avg_fps, len(detections), stable_count)
                
                # Add timestamp
                cv2.putText(frame, f"Frame: {self.frame_count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                prev_time = current_time
            
            # Display frame
            if last_frame is not None:
                cv2.imshow("🎥 PHASE 4 — Live Camera Detection", last_frame if paused else frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n✋ Stopping demonstration...")
                break
            elif key == ord('s'):
                filename = f"screenshot_{self.frame_count}.png"
                cv2.imwrite(filename, frame if not paused else last_frame)
                print(f"📸 Screenshot saved: {filename}")
            elif key == ord(' '):
                paused = not paused
                status = "PAUSED" if paused else "RUNNING"
                print(f"⏸ {status}")
        
        self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.cap.release()
        cv2.destroyAllWindows()
        print("✅ Demo ended")

    def demo_with_info(self):
        """Run demo with detailed information display"""
        print("\n" + "="*60)
        print("📊 PHASE 4 COMPONENT STATUS")
        print("="*60)
        print(f"✅ Camera Detector: Ready")
        print(f"✅ Scene Graph Engine: Ready")
        print(f"✅ Stabilization Buffer: Ready (buffer_size=5)")
        print(f"✅ Screen Monitor: Ready")
        print("\n" + "="*60)
        print("🎥 STARTING LIVE DEMONSTRATION")
        print("="*60)
        print(f"\nCamera Resolution: 640x480 @ 30 FPS")
        print(f"Detection Mode: Real-time YOLOv8 (CPU)")
        print(f"Scene Understanding: Spatial reasoning enabled")
        print(f"\nControls:")
        print(f"  'q' - Quit")
        print(f"  's' - Screenshot")
        print(f"  'space' - Pause/Resume")
        print("\n" + "-"*60 + "\n")
        
        self.run()


if __name__ == "__main__":
    try:
        print("\n🚀 Initializing PHASE 4 Camera Visual Demonstration...")
        demo = CameraVisualDemo()
        demo.demo_with_info()
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("  - Verify camera is connected")
        print("  - Check camera permissions")
        print("  - Try another camera device (modify cv2.VideoCapture(0))")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
