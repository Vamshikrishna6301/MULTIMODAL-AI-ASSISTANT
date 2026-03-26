#!/usr/bin/env python3
"""
GPU-Only Voice Assistant Launcher
Properly configures CUDA paths and runs in GPU-exclusive mode
"""
import os
import sys

# Add PyTorch CUDA libraries to PATH BEFORE importing PyTorch
torch_lib_path = r"c:\Users\ramsa\OneDrive\Desktop\multimodal-assistive-ai\.venv-1\Lib\site-packages\torch\lib"
os.environ["PATH"] = f"{torch_lib_path};{os.environ.get('PATH', '')}"

# Set other helpful environment variables
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Use only GPU 0

# Now import the application 
from voice.voice_loop import VoiceLoop

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 GPU-EXCLUSIVE VOICE ASSISTANT (CUDA ENABLED)")
    print("=" * 70)
    
    # Verify CUDA is available
    try:
        import torch
        if not torch.cuda.is_available():
            print("❌ ERROR: CUDA is not available!")
            print("   Make sure NVIDIA GPU drivers are installed.")
            sys.exit(1)
        print(f"✅ GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"✅ CUDA Version: {torch.version.cuda}")
        print(f"✅ PyTorch Version: {torch.__version__}\n")
    except Exception as e:
        print(f"❌ Failed to verify CUDA: {e}")
        sys.exit(1)
    
    try:
        assistant = VoiceLoop()
        assistant.start_production()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
