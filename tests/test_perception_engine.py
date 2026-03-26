import sys
import os

# Add project root to Python path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from execution.executor import ExecutionEngine
from core.context_memory import ContextMemory

engine = ExecutionEngine(ContextMemory())

print("\n--- TEST 1: READ SCREEN ---")

decision = {
    "status": "APPROVED",
    "action": "READ_SCREEN"
}

response = engine.execute(decision)
print(response.spoken_message)


print("\n--- TEST 2: NEXT ITEM ---")

decision = {
    "status": "APPROVED",
    "action": "NEXT_ITEM"
}

response = engine.execute(decision)
print(response.spoken_message)


print("\n--- TEST 3: ACTIVATE ITEM ---")

decision = {
    "status": "APPROVED",
    "action": "ACTIVATE_ITEM"
}

response = engine.execute(decision)
print(response.spoken_message)