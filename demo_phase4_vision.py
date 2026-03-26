#!/usr/bin/env python3
"""
Phase 4 — Vision Integration Demo
Demonstrates all advanced vision features
"""
import os
import sys
import time

# Setup GPU path
torch_lib_path = r"c:\Users\ramsa\OneDrive\Desktop\multimodal-assistive-ai\.venv-1\Lib\site-packages\torch\lib"
os.environ["PATH"] = f"{torch_lib_path};{os.environ.get('PATH', '')}"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from execution.vision.screen_capture import ScreenCapture
from execution.vision.ocr_engine import OCREngine
from execution.vision.camera_detector import CameraDetector
from execution.vision.scene_graph_engine import SceneGraphEngine
from execution.vision.stabilization_buffer import StabilizationBuffer
from execution.vision.screen_monitoring_engine import ScreenMonitoringEngine
from execution.vision.vision_mode_controller import VisionModeController


def demo_screen_capture():
    """Demo: Screen capture and OCR"""
    print("\n" + "=" * 70)
    print("📸 DEMO 1: Screen Capture & OCR Reading")
    print("=" * 70)
    
    try:
        screen_capture = ScreenCapture()
        ocr_engine = OCREngine()
        
        print("📷 Capturing screen...")
        frame = screen_capture.capture()
        
        print("📖 Extracting text via OCR...")
        text = ocr_engine.extract_text(frame)
        
        if text:
            print(f"✅ Extracted text (first 200 chars):\n{text[:200]}...")
        else:
            print("⚠️  No text detected on screen")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_scene_understanding():
    """Demo: Scene graph and spatial relationships"""
    print("\n" + "=" * 70)
    print("🧠 DEMO 2: Scene Understanding & Relationships")
    print("=" * 70)
    
    try:
        scene_graph = SceneGraphEngine()
        
        # Simulated detections
        detections = [
            {"label": "person", "confidence": 0.95, "bbox": [0.2, 0.1, 0.4, 0.8]},
            {"label": "chair", "confidence": 0.88, "bbox": [0.25, 0.5, 0.45, 0.95]},
            {"label": "phone", "confidence": 0.92, "bbox": [0.35, 0.2, 0.45, 0.35]},
        ]
        
        print("🎯 Analyzing scene with 3 sample detections...")
        scene = scene_graph.analyze_frame(detections)
        
        print(f"📊 Scene description: {scene['scene_description']}")
        
        if scene['relationships']:
            print("🔗 Detected relationships:")
            for rel in scene['relationships']:
                print(f"  - {rel['object1']} is {rel['spatial_relationship']} {rel['object2']}")
        
        if scene['interactions']:
            print("🤝 Inferred interactions:")
            for interaction in scene['interactions']:
                print(f"  - {interaction}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_stabilization():
    """Demo: Detection stabilization for consistent results"""
    print("\n" + "=" * 70)
    print("🎯 DEMO 3: Detection Stabilization Buffer")
    print("=" * 70)
    
    try:
        stabilizer = StabilizationBuffer(buffer_size=5, min_duration=0.5)
        
        # Simulate multiple frames with detection noise
        frames = [
            [{"label": "person", "confidence": 0.98}],
            [{"label": "person", "confidence": 0.91}],
            [{"label": "person", "confidence": 0.96}],
            [{"label": "person", "confidence": 0.94}, {"label": "phone", "confidence": 0.85}],
            [{"label": "person", "confidence": 0.89}, {"label": "phone", "confidence": 0.91}],
        ]
        
        for i, frame_detections in enumerate(frames):
            stable = stabilizer.add_detections(frame_detections)
            print(f"Frame {i+1}: Detected {len(frame_detections)} objects → Stabilized {len(stable)} objects")
            
            if i == 4:
                person_count = stabilizer.get_stable_count("person")
                print(f"✅ Stable person count: {person_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_camera_detection():
    """Demo: Camera-based object detection"""
    print("\n" + "=" * 70)
    print("📹 DEMO 4: Live Camera Detection")
    print("=" * 70)
    
    try:
        camera = CameraDetector()
        
        print("🎥 Starting camera detection for 5 seconds...")
        camera.start()
        
        for i in range(5):
            time.sleep(1)
            detections = camera.get_latest_detections()
            tracked = camera.get_tracked_objects()
            
            print(f"  [{i+1}s] Detected: {len(detections)} objects, Tracked: {len(tracked)} objects")
        
        camera.stop()
        print("✅ Camera demo completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_vision_modes():
    """Demo: Vision mode controller"""
    print("\n" + "=" * 70)
    print("🎛️  DEMO 5: Vision Mode Controller")
    print("=" * 70)
    
    try:
        mode_controller = VisionModeController()
        
        modes = ["SILENT", "PASSIVE", "ALERT", "SAFETY"]
        
        for mode in modes:
            mode_controller.set_mode(mode)
            print(f"✅ Switched to {mode} mode")
            time.sleep(0.5)
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("\n" + "=" * 70)
    print("🚀 PHASE 4 — VISION INTEGRATION DEMO")
    print("Advanced Multimodal Vision Features")
    print("=" * 70)
    
    demos = [
        ("Screen Capture & OCR", demo_screen_capture),
        ("Scene Understanding", demo_scene_understanding),
        ("Stabilization Buffer", demo_stabilization),
        ("Camera Detection", demo_camera_detection),
        ("Vision Modes", demo_vision_modes),
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print(f"  {len(demos)+1}. Run all demos")
    print(f"  {0}. Exit")
    
    while True:
        choice = input("\nSelect demo (0-6): ").strip()
        
        if choice == "0":
            print("Exiting...")
            break
        elif choice == str(len(demos) + 1):
            for name, demo_func in demos:
                print(f"\n{'='*70}")
                print(f"Running: {name}")
                demo_func()
                time.sleep(1)
            break
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(demos):
                    demos[idx][1]()
                else:
                    print("Invalid choice")
            except (ValueError, IndexError):
                print("Invalid input")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
