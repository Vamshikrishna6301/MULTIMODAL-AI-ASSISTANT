from knowledge.knowledge_engine import KnowledgeEngine

engine = KnowledgeEngine()

tests = [
    "who is einstein",
    "what is machine learning",
    "tell me about python programming",
    "define gravity",
    "who was alan turing",
    "random nonsense text"
]

for t in tests:

    decision = {
        "target": t
    }

    response = engine.handle(decision)

    print("\nQuery:", t)
    print("Success:", response.success)
    print("Answer:", response.spoken_message)