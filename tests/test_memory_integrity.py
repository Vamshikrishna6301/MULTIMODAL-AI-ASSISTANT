from core.fusion_engine import FusionEngine


def test_memory_not_leaking_state():
    fusion = FusionEngine()

    for _ in range(100):
        fusion.process_text("open chrome")
        fusion.process_text("delete file.txt")
        fusion.process_text("cancel")

    # Ensure system still functions normally
    result = fusion.process_text("open notepad").to_dict()
    assert result["status"] in ["APPROVED", "NEEDS_CONFIRMATION"]