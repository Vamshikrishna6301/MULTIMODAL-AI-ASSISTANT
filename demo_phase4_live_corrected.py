#!/usr/bin/env python3
"""
PHASE 4 — CORRECTED LIVE CAMERA VISUAL DEMONSTRATION
Demonstrates real-time object detection with correct component APIs
"""

import cv2
import sys
import time
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.vision.camera_detector import CameraDetector
from execution.vision.scene_graph_engine import SceneGraphEngine
from execution.vision.stabilization_buffer import StabilizationBuffer


class Phase4LiveDemo:
    """Live camera demonstrator with corrected APIs"""
    
    def __init__(self):
        """Initialize demo components"""
        print("\n" + "="*70)
        print(" 🎬 PHASE 4 — LIVE CAMERA VISUAL DEMONSTRATION")
        print("="*70 + "\n")
        
        # Check camera availability
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("❌ Camera not available")
            raise RuntimeError("Cannot open camera")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("✅ Camera initialized (640x480)")
        
        # Initialize Phase 4 components
        self.detector = CameraDetector()
        self.scene_graph = SceneGraphEngine()
        self.stabilization = StabilizationBuffer(buffer_size=5, min_duration=0.5)
        
        print("✅ CameraDetector loaded")
        print("✅ SceneGraphEngine loaded")
        print("✅ StabilizationBuffer loaded")
        
        self.frame_count = 0
        self.detections_list = []
        
        print("\n" + "-"*70)
        print("Controls: 'q' = quit, 's' = screenshot, 'space' = pause")
        print("-"*70 + "\n")

    def process_frame(self, frame):
        """Process single frame with Phase 4 components"""
        # Use CameraDetector's detection (manual for demo)
        # In real usage, detector runs in background thread
        import torch
        from ultralytics import YOLO
        
        model = YOLO("yolov8n.pt")
        model.to("cpu")
        
        results = model(frame)
        detections = []
        
        if results:
            for result in results:
                if hasattr(result, 'boxes'):
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        label = result.names[cls]
                        
                        # Normalize to 0-1
                        h, w = frame.shape[:2]
                        detections.append({
                            "label": label,
                            "confidence": conf,
                            "bbox": [x1/w, y1/h, x2/w, y2/h]
                        })
        
        return detections

    def draw_frame(self, frame, detections, scene_data):
        """Draw detections and annotations on frame"""
        h, w = frame.shape[:2]
        
        # Draw bounding boxes
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            x1, y1 = int(x1 * w), int(y1 * h)
            x2, y2 = int(x2 * w), int(y2 * h)
            conf = det["confidence"]
            
            color = (0, 255, 0) if conf > 0.6 else (0, 165, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{det['label']} {conf:.2f}", (x1, y1-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw scene understanding
        if scene_data and scene_data.get("scene_description"):
            text = scene_data["scene_description"][:60]
            cv2.putText(frame, f"Scene: {text}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Draw relationships
        if scene_data and scene_data.get("relationships"):
            for i, rel in enumerate(scene_data["relationships"][:2]):
                cv2.putText(frame, f"• {rel[:50]}", (10, 60 + i*20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Draw frame info
        cv2.putText(frame, f"Frame: {self.frame_count}", (w-150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Objects: {len(detections)}", (w-150, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    def run(self):
        """Run live demonstration"""
        print("🎥 Starting live camera feed...")
        print("   Detecting objects | Analyzing relationships | Stabilizing detections\n")
        
        frame_times = []
        start_time = time.time()
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                frame_start = time.time()
                
                # Process frame with Phase 4 components
                detections = self.process_frame(frame)
                self.detections_list.append(detections)
                
                # Stabilize detections
                stabilized = self.stabilization.add_detections(detections)
                
                # Analyze scene
                scene_data = self.scene_graph.analyze_frame(detections)
                
                # Draw on frame
                self.draw_frame(frame, detections, scene_data)
                
                # Display
                cv2.imshow("🎥 PHASE 4 — Live Detection", frame)
                
                # Timing
                frame_time = time.time() - frame_start
                frame_times.append(frame_time)
                if len(frame_times) > 30:
                    frame_times.pop(0)
                
                # Print status every 10 frames
                if self.frame_count % 10 == 0:
                    avg_fps = len(frame_times) / sum(frame_times) if frame_times else 0
                    print(f"  Frame {self.frame_count}: {len(detections)} objects | "
                          f"FPS: {avg_fps:.1f} | Scene: {scene_data.get('scene_description', 'analyzing...')[:50]}")
                
                # Handle keyboard
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    filename = f"phase4_screenshot_{self.frame_count}.png"
                    cv2.imwrite(filename, frame)
                    print(f"  📸 Screenshot saved: {filename}")
                
        except KeyboardInterrupt:
            print("\n⏹️  Stopped by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.cap.release()
        cv2.destroyAllWindows()
        
        elapsed = self.frame_count / 30  # Approx 30 fps
        print(f"\n✅ Demonstration complete:")
        print(f"   Frames processed: {self.frame_count}")
        print(f"   Objects detected: {len(self.detections_list)}")
        if self.detections_list:
            avg_objs = sum(len(d) for d in self.detections_list) / len(self.detections_list)
            print(f"   Avg objects per frame: {avg_objs:.1f}")


if __name__ == "__main__":
    try:
        demo = Phase4LiveDemo()
        demo.run()
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("  - Verify camera is connected")
        print("  - Check camera permissions")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
