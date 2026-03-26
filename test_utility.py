from utility.utility_engine import UtilityEngine

engine = UtilityEngine()

tests = [
    {"action": "CALCULATE", "target": "2 + 3 * 4"},
    {"action": "CALCULATE", "target": "sqrt(16)"},
    {"action": "CALCULATE", "target": "sin(pi/2)"},
    {"action": "CALCULATE", "target": "2^10"},
    {"action": "GET_TIME", "target": None},
]

for test in tests:
    print("\nTest:", test)
    response = engine.handle(test)
    print("Response:", response.spoken_message)