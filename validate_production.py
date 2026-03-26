#!/usr/bin/env python3
"""
Production Startup Validation & Health Check
Verifies all infrastructure components before running the full application
"""

import os
import sys
import time
from datetime import datetime

# Set CUDA path before imports
torch_lib_path = r"c:\Users\ramsa\OneDrive\Desktop\multimodal-assistive-ai\.venv-1\Lib\site-packages\torch\lib"
os.environ["PATH"] = f"{torch_lib_path};{os.environ.get('PATH', '')}"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

def validate_imports():
    """Verify all essential imports are available"""
    print("\n🔍 VALIDATING IMPORTS")
    print("=" * 60)
    
    imports_to_check = [
        ("torch", "PyTorch"),
        ("faster_whisper", "faster-whisper STT"),
        ("webrtcvad", "WebRTC VAD"),
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("psutil", "psutil (system monitoring)"),
    ]
    
    failed = []
    for module_name, display_name in imports_to_check:
        try:
            __import__(module_name)
            print(f"✅ {display_name:30} OK")
        except ImportError:
            print(f"❌ {display_name:30} MISSING")
            failed.append(display_name)
    
    return len(failed) == 0, failed


def validate_gpu():
    """Verify GPU/CUDA configuration"""
    print("\n⚡ VALIDATING GPU CONFIGURATION")
    print("=" * 60)
    
    try:
        import torch
        
        cuda_available = torch.cuda.is_available()
        print(f"GPU Available: {'✅' if cuda_available else '❌'} {cuda_available}")
        
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            cuda_version = torch.version.cuda
            pytorch_version = torch.__version__
            
            print(f"GPU Device:    {device_name}")
            print(f"CUDA Version:  {cuda_version}")
            print(f"PyTorch:       {pytorch_version}")
            
            # Test CUDA operations
            try:
                test_tensor = torch.randn(2, 3).cuda()
                print(f"CUDA Compute:  ✅ Working")
                return True
            except Exception as e:
                print(f"CUDA Compute:  ❌ Failed: {e}")
                return False
        else:
            print("⚠️  GPU not available - will use CPU (slower)")
            return True
            
    except Exception as e:
        print(f"❌ GPU validation failed: {e}")
        return False


def validate_production_config():
    """Verify production configuration loads correctly"""
    print("\n⚙️  VALIDATING PRODUCTION CONFIGURATION")
    print("=" * 60)
    
    try:
        from config_production import (
            get_config, AUDIO_CONFIG, VISION_CONFIG, 
            COMPUTE_CONFIG, MONITORING_CONFIG
        )
        
        config = get_config()
        print(f"✅ Configuration loaded successfully")
        
        # Display key settings
        print(f"\n📝 Configuration Summary:")
        print(f"   Audio Sample Rate:      {AUDIO_CONFIG['sample_rate']} Hz")
        print(f"   Vision Resolution:      {VISION_CONFIG['resolution']}")
        print(f"   Whisper Device:         {COMPUTE_CONFIG['whisper_device']}")
        print(f"   Monitoring Enabled:     {bool(MONITORING_CONFIG)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_logging():
    """Verify logging infrastructure works"""
    print("\n📝 VALIDATING LOGGING INFRASTRUCTURE")
    print("=" * 60)
    
    try:
        from infrastructure.production_logger import get_production_logger
        
        logger = get_production_logger()
        app_logger = logger.get_logger("validation")
        
        print(f"✅ Logger initialized successfully")
        
        # Test logging
        app_logger.info("Test info message")
        app_logger.warning("Test warning message")
        
        print(f"✅ Logging operations successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Logging validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_monitoring():
    """Verify monitoring systems initialize correctly"""
    print("\n💚 VALIDATING MONITORING INFRASTRUCTURE")
    print("=" * 60)
    
    try:
        from infrastructure.system_monitor import (
            get_health_monitor, get_performance_tracker, get_resource_cleaner
        )
        
        # Health monitor
        health_monitor = get_health_monitor()
        print(f"✅ Health monitor initialized")
        
        # Performance tracker
        perf_tracker = get_performance_tracker()
        print(f"✅ Performance tracker initialized")
        
        # Resource cleaner
        resource_cleaner = get_resource_cleaner()
        print(f"✅ Resource cleaner initialized")
        
        # Start health monitor briefly to test
        health_monitor.start()
        time.sleep(2)
        health_monitor.stop()
        
        health_status = health_monitor.get_current_health()
        print(f"\n📊 System Health Status:")
        print(f"   CPU Usage:              {health_status.cpu_percent:.1f}%")
        print(f"   Memory Usage:           {health_status.memory_percent:.1f}%")
        if health_status.gpu_available:
            print(f"   GPU Memory Used:        {health_status.gpu_memory_used:.0f}MB")
            print(f"   GPU Memory Total:       {health_status.gpu_memory_total:.0f}MB")
        print(f"   Threads Active:         {health_status.thread_count}")
        print(f"   Status Level:           {health_status.status_level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_error_handling():
    """Verify error handling infrastructure"""
    print("\n🛡️  VALIDATING ERROR HANDLING")
    print("=" * 60)
    
    try:
        from infrastructure.error_handling import (
            get_error_handler, retry_with_backoff, RetryConfig, CircuitBreaker
        )
        
        # Error handler
        error_handler = get_error_handler()
        print(f"✅ Error handler initialized")
        
        # Test retry decorator
        attempt_count = [0]
        
        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.1))
        def test_retry():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ValueError("Test error")
            return "Success"
        
        try:
            result = test_retry()
            print(f"✅ Retry decorator working (took {attempt_count[0]} attempts)")
        except Exception as e:
            print(f"❌ Retry decorator failed: {e}")
            return False
        
        # Test circuit breaker
        breaker = CircuitBreaker(failure_threshold=2, name="test")
        print(f"✅ Circuit breaker initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_core_components():
    """Verify core application components can be imported"""
    print("\n🎯 VALIDATING CORE COMPONENTS")
    print("=" * 60)
    
    components = [
        ("voice.voice_loop", "VoiceLoop"),
        ("core.intent_parser", "IntentParser"),
        ("execution.executor", "Executor"),
        ("execution.vision.vision_executor", "VisionExecutor"),
    ]
    
    failed = []
    for module_path, component_name in components:
        try:
            module = __import__(module_path, fromlist=[component_name])
            getattr(module, component_name)
            print(f"✅ {component_name:30} OK")
        except Exception as e:
            print(f"❌ {component_name:30} FAILED: {str(e)[:40]}")
            failed.append((component_name, str(e)))
    
    return len(failed) == 0, failed


def main():
    """Run all validation checks"""
    print("\n" + "=" * 60)
    print("🚀 PRODUCTION STARTUP VALIDATION")
    print("=" * 60)
    print(f"Validation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    validation_results = {}
    
    # Run all validators
    validators = [
        ("Imports", validate_imports),
        ("GPU Configuration", validate_gpu),
        ("Production Configuration", validate_production_config),
        ("Logging Infrastructure", validate_logging),
        ("Monitoring Infrastructure", validate_monitoring),
        ("Error Handling", validate_error_handling),
        ("Core Components", validate_core_components),
    ]
    
    for validator_name, validator_func in validators:
        try:
            if validator_name == "Imports" or validator_name == "Core Components":
                result, details = validator_func()
                validation_results[validator_name] = (result, details)
            else:
                result = validator_func()
                validation_results[validator_name] = (result, None)
        except Exception as e:
            print(f"\n❌ Validator crashed: {e}")
            validation_results[validator_name] = (False, str(e))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result, _ in validation_results.values() if result)
    total = len(validation_results)
    
    for validator_name, (result, details) in validation_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {validator_name}")
        if details and not result:
            if isinstance(details, list):
                for detail in details[:2]:  # Show first 2 failures
                    print(f"          → {detail}")
            elif isinstance(details, str):
                print(f"          → {details[:60]}")
    
    print(f"\n{'=' * 60}")
    print(f"Overall: {passed}/{total} validators passed")
    
    if passed == total:
        print("✅ All systems ready for production!")
        print(f"{'=' * 60}\n")
        return 0
    else:
        print("❌ Some validations failed. Please fix issues before running.")
        print(f"{'=' * 60}\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
