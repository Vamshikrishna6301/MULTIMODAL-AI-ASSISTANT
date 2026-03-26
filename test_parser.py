from core.intent_parser import IntentParser
from core.intent_schema import Mode

parser = IntentParser()

tests = [
    "open the chrome.",
    "please open chrome",
    "delete the report.pdf",
    "search for transformers",
    "what is bert",
    "type hello world",
    "shutdown the system"
]

for t in tests:
    intent = parser.parse(t, current_mode=Mode.COMMAND)

    print("\n" + "=" * 50)
    print("Input:", t)
    print("Intent Type:", intent.intent_type.name)
    print("Action:", intent.action)
    print("Target:", intent.target)
    print("Parameters:", intent.parameters)
    print("Mode:", intent.mode.name)
    print("Confidence:", round(intent.confidence, 3))
    print("High Confidence:", intent.is_high_confidence())
    print("Needs Clarification:", intent.needs_clarification())
    print("Requires Confirmation:", intent.requires_confirmation)
    print("Risk Level:", intent.risk_level)
    print("Is Dangerous:", intent.is_dangerous())
    print("Is Executable:", intent.is_executable())
    print("Blocked Reason:", intent.blocked_reason)

    if intent.entities:
        print("Entities:")
        for k, v in intent.entities.items():
            print(f"  - {k}: {v.value} (conf={v.confidence})")
    else:
        print("Entities: None")

    print("Structured Output:", intent.to_dict())