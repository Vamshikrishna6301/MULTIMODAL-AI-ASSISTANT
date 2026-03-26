from execution.executor import ExecutionEngine
from core.context_memory import ContextMemory


def run_test(name, decision):
    print(f"\n=== TEST: {name} ===")
    engine = ExecutionEngine(ContextMemory())
    response = engine.execute(decision)
    print("Success:", response.success)
    print("Error Code:", response.error_code)
    print("Spoken:", response.spoken_message)


engine = ExecutionEngine(ContextMemory())

# 1️⃣ Execution without approval
run_test("Not Approved", {
    "status": "BLOCKED",
    "action": "OPEN_APP",
    "target": "calculator",
    "risk_level": 1
})

# 2️⃣ Safety blocked
run_test("Blocked by Safety", {
    "status": "APPROVED",
    "action": "OPEN_APP",
    "blocked_reason": "Unsafe",
    "risk_level": 1
})

# 3️⃣ Dangerous without confirmation
run_test("Dangerous No Confirmation", {
    "status": "APPROVED",
    "action": "SYSTEM_CONTROL",
    "target": "shutdown",
    "risk_level": 9,
    "requires_confirmation": True
})

# 4️⃣ Dangerous WITH confirmation
run_test("Dangerous With Confirmation", {
    "status": "APPROVED",
    "action": "SYSTEM_CONTROL",
    "target": "shutdown",
    "risk_level": 9,
    "requires_confirmation": True,
    "confirmed": True
})

# 5️⃣ Missing action
run_test("Missing Action", {
    "status": "APPROVED",
    "risk_level": 1
})

# 6️⃣ Malformed decision
run_test("Malformed Decision", None)