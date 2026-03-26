from core.intent_parser import IntentParser
from core.context_memory import ContextMemory
from core.mode_manager import ModeManager
from core.safety_engine import SafetyEngine

parser = IntentParser()
memory = ContextMemory()
mode_manager = ModeManager()
safety = SafetyEngine()

commands = [
    "open chrome",
    "delete report.pdf",
    "delete all files in system",
    "shutdown now"
]

for cmd in commands:
    print("\n" + "=" * 60)
    print("Input:", cmd)

    # Parse
    intent = parser.parse(cmd, current_mode=mode_manager.get_mode())

    # Enrich with memory
    intent = memory.enrich(intent)

    # Update memory
    memory.update(intent)

    # Evaluate safety
    intent = safety.evaluate(intent, mode_manager.get_mode())

    print("Intent Type:", intent.intent_type.name)
    print("Action:", intent.action)
    print("Target:", intent.target)
    print("Risk Level:", intent.risk_level)
    print("Requires Confirmation:", intent.requires_confirmation)
    print("Blocked Reason:", intent.blocked_reason)
    print("Is Dangerous:", intent.is_dangerous())
    print("Is Executable:", intent.is_executable())
    print("Context:", intent.context)
    print("Structured Output:", intent.to_dict())