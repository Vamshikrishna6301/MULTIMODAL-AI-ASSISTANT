#!/usr/bin/env python3
"""
PHASE 4 — TEXT-BASED VISUAL DEMONSTRATION
Shows camera output analysis in terminal with real-time stats
"""

import cv2
import sys
import time
import numpy as np
from pathlib import Path
from collections import deque

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.vision.scene_graph_engine import SceneGraphEngine
from execution.vision.stabilization_buffer import StabilizationBuffer


class Phase4TextVisualDemo:
    """Terminal-based camera demonstration with text output"""
    
    def __init__(self):
        """Initialize demo components"""
        print("\n" + "="*80)
        print(" 🎬 PHASE 4 — LIVE CAMERA VISUAL ANALYSIS (Text Output)")
        print("="*80 + "\n")
        
        # Check camera availability
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("❌ Camera not available")
            raise RuntimeError("Cannot open camera")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("✅ Camera initialized: 640×480 @ 30 FPS")
        
        # Initialize Phase 4 components
        self.scene_graph = SceneGraphEngine()
        self.stabilization = StabilizationBuffer(buffer_size=5, min_duration=0.5)
        
        print("✅ Scene Graph Engine loaded")
        print("✅ Stabilization Buffer loaded\n")
        
        # Initialize YOLO for detection
        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self.model.to("cpu")
            print("✅ YOLOv8 Detector loaded (CPU mode)\n")
        except Exception as e:
            print(f"❌ YOLO load failed: {e}")
            raise
        
        self.frame_count = 0
        self.detection_history = deque(maxlen=100)
        self.prev_objects = set()
        
        print("-"*80)
        print("Reading camera frames... Press Ctrl+C to stop")
        print("-"*80 + "\n")

    def detect_objects(self, frame):
        """Detect objects using YOLOv8"""
        results = self.model(frame, verbose=False)
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
                        bbox_norm = [x1/w, y1/h, x2/w, y2/h]
                        
                        if conf > 0.3:  # Low threshold for demo
                            detections.append({
                                "label": label,
                                "confidence": conf,
                                "bbox": bbox_norm
                            })
        
        return detections

    def print_frame_analysis(self, frame_num, detections, scene_data):
        """Print formatted frame analysis"""
        # Clear screen effect (terminal scrolling)
        if frame_num % 30 == 0:
            print("\n" + "="*80)
            print(f"FRAME {frame_num} — ANALYSIS")
            print("="*80)
        
        # Show detections
        print(f"\n📹 Frame #{frame_num}")
        print(f"   Time: {time.time():.2f}")
        
        if detections:
            print(f"   🎯 Objects Detected: {len(detections)}")
            for det in detections:
                conf_bar = "█" * int(det["confidence"] * 10) + "░" * (10 - int(det["confidence"] * 10))
                print(f"      • {det['label']:<12} [{conf_bar}] {det['confidence']:.2f}")
        else:
            print(f"   🎯 Objects Detected: None")
        
        # Show scene understanding
        if scene_data and scene_data.get("scene_description"):
            print(f"\n   🧠 Scene Understanding:")
            print(f"      {scene_data['scene_description']}")
        
        # Show relationships
        if scene_data and scene_data.get("relationships"):
            print(f"\n   🔗 Spatial Relationships ({len(scene_data['relationships'])}):")
            for rel in scene_data["relationships"][:3]:
                print(f"      • {rel}")
            if len(scene_data["relationships"]) > 3:
                print(f"      ... and {len(scene_data['relationships']) - 3} more")
        
        # Show interactions
        if scene_data and scene_data.get("interactions"):
            print(f"\n   🤝 Inferred Interactions ({len(scene_data['interactions'])}):")
            for inter in scene_data["interactions"][:2]:
                print(f"      • {inter}")

    def print_statistics(self, frame_times, all_detections):
        """Print aggregate statistics"""
        print("\n" + "="*80)
        print("📊 SESSION STATISTICS")
        print("="*80)
        
        if frame_times:
            avg_fps = len(frame_times) / sum(frame_times) if sum(frame_times) > 0 else 0
            print(f"   Frames Processed: {self.frame_count}")
            print(f"   Average FPS: {avg_fps:.1f}")
            print(f"   Min/Max Frame Time: {min(frame_times)*1000:.1f}ms / {max(frame_times)*1000:.1f}ms")
        
        if all_detections:
            unique_labels = set()
            total_detections = 0
            for det_list in all_detections:
                for det in det_list:
                    unique_labels.add(det["label"])
                    total_detections += 1
            
            print(f"\n   Total Detections: {total_detections}")
            print(f"   Unique Objects: {len(unique_labels)}")
            print(f"   Average per Frame: {total_detections / max(1, len(all_detections)):.1f}")
            print(f"\n   Objects Found:")
            for label in sorted(unique_labels):
                count = sum(1 for d in all_detections for det in d if det["label"] == label)
                print(f"      • {label}: {count} detections")

    def run(self):
        """Run live text-based demonstration"""
        frame_times = []
        
        try:
            while self.frame_count < 100:  # 100 frames demo
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                frame_start = time.time()
                
                # Detect objects
                detections = self.detect_objects(frame)
                self.detection_history.append(detections)
                
                # Stabilize detections
                stabilized = self.stabilization.add_detections(detections)
                
                # Analyze scene
                scene_data = self.scene_graph.analyze_frame(detections)
                
                # Print analysis
                self.print_frame_analysis(self.frame_count, detections, scene_data)
                
                # Timing
                frame_time = time.time() - frame_start
                frame_times.append(frame_time)
                if len(frame_times) > 30:
                    frame_times.pop(0)
                
                # Show a summary every 30 frames
                if self.frame_count % 30 == 0:
                    print(f"\n   ⏱️  Processing Speed: {1/frame_time:.1f} FPS")
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopped by user")
        finally:
            self.cleanup(frame_times)

    def cleanup(self, frame_times):
        """Clean up and show final statistics"""
        self.cap.release()
        
        # Collect all detections
        all_detections = list(self.detection_history)
        
        self.print_statistics(frame_times, all_detections)
        
        print("\n" + "="*80)
        print("✅ PHASE 4 VISUAL DEMONSTRATION COMPLETE")
        print("="*80)
        print("\n📋 Next Steps:")
        print("   1. Run main application: python main.py")
        print("   2. Try vision commands: 'What do you see?'")
        print("   3. Check scene understanding with objects in view")
        print("\n")


if __name__ == "__main__":
    try:
        demo = Phase4TextVisualDemo()
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
