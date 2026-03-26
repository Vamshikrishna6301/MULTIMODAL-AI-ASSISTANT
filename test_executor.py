from execution.executor import ExecutionEngine
import time

engine = ExecutionEngine()


def run_test(test_name, decision):
    print("\n==============================")
    print("TEST:", test_name)
    print("Decision:", decision)

    response = engine.execute(decision)

    print("Response:", response)
    print("Spoken Message:", response.spoken_message)
    print("==============================")


# ----------------------------
# SAFE TESTS
# ----------------------------

run_test(
    "Open Notepad",
    {"status": "APPROVED", "action": "OPEN_APP", "target": "notepad"}
)

time.sleep(2)

run_test(
    "Search Transformers",
    {"status": "APPROVED", "action": "SEARCH", "target": "transformers in ai"}
)

time.sleep(2)

run_test(
    "Type Text (Focus Notepad!)",
    {"status": "APPROVED", "action": "TYPE_TEXT", "target": "Hello from Assistive AI"}
)

time.sleep(2)

run_test(
    "File Delete (must exist in Desktop/Documents/Downloads)",
    {"status": "APPROVED", "action": "FILE_OPERATION", "target": "test_delete.txt"}
)

# ----------------------------
# ERROR TESTS (SAFE)
# ----------------------------

run_test(
    "Invalid App",
    {"status": "APPROVED", "action": "OPEN_APP", "target": "fakeapp123"}
)

run_test(
    "Invalid File",
    {"status": "APPROVED", "action": "FILE_OPERATION", "target": "fakefile.txt"}
)

run_test(
    "Unsupported Action",
    {"status": "APPROVED", "action": "UNKNOWN_ACTION", "target": None}
)

# ----------------------------
# SYSTEM CONTROL TEST (DANGEROUS)
# Uncomment ONLY if you want to test
# ----------------------------

# run_test(
#     "System Shutdown",
#     {"status": "APPROVED", "action": "SYSTEM_CONTROL", "target": "shutdown"}
# )