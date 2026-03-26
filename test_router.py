from router.decision_router import DecisionRouter

router = DecisionRouter()

tests = [
    {"status": "APPROVED", "action": "OPEN_APP", "target": "notepad"},
    {"status": "APPROVED", "action": "CALCULATE", "target": "2 + 5 * 3"},
    {"status": "APPROVED", "action": "KNOWLEDGE_QUERY", "target": "Who is virat?"},
    {"status": "APPROVED", "action": "KNOWLEDGE_QUERY", "target": "What is AI?"},
    {"status": "APPROVED", "action": "KNOWLEDGE_QUERY", "target": "Explain quantum computing"},
]

for test in tests:
    print("\n------------------------------")
    print("Decision:", test)
    response = router.route(test)
    print("Spoken:", response.spoken_message)