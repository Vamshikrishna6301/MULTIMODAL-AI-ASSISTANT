from core.context_memory import ContextMemory
from execution.executor import ExecutionEngine


def run_vision_test(task_type="describe"):

    context = ContextMemory()
    engine = ExecutionEngine(context)

    decision = {
        "status": "APPROVED",
        "action": "VISION",
        "target": "screen",
        "task": task_type,  # "describe" or "read_text"
        "risk_level": 0,
        "requires_confirmation": False,
        "confirmed": False
    }

    response = engine.execute(decision)

    print("\n===== VISION TEST RESULT =====")
    print("Success:", response.success)
    print("Category:", response.category)
    print("Spoken Message:\n")
    print(response.spoken_message)
    print("\nError Code:", response.error_code)
    print("Technical Message:", response.technical_message)
    print("================================\n")


if __name__ == "__main__":

    print("Running SCREEN CAPTURE test...")
    run_vision_test("describe")

    print("Running OCR READ_TEXT test...")
    run_vision_test("read_text")