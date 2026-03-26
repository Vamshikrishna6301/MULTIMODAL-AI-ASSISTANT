"""
Phase 2 Integration Demo
Shows the complete intent parsing pipeline with safety rules
"""

from core import IntentParser, ModeManager, SafetyRules, Mode


def main():
    print("\n" + "="*70)
    print("🧪 Phase 2 Integration Demo - Intent Processing Pipeline")
    print("="*70 + "\n")

    parser = IntentParser()
    manager = ModeManager()
    safety = SafetyRules()

    test_cases = [
        ("open chrome", Mode.LISTENING),
        ("type hello world", Mode.DICTATION),
        ("delete file", Mode.COMMAND),
        ("what is python", Mode.LISTENING),
        ("disable assistant", Mode.COMMAND),
        ("delete all files", Mode.COMMAND),
    ]

    for text, mode in test_cases:
        print(f'Input: "{text}" (Mode: {mode.name})')

        intent = parser.parse(text, mode)
        allowed, reason, confirm = safety.validate(intent)

        print(f"  📊 Intent Type: {intent.intent_type.name}")
        print(f"  🎯 Action: {intent.action}")
        if intent.target:
            print(f"  📍 Target: {intent.target}")
        print(f"  📈 Confidence: {intent.confidence:.2f} ({intent.confidence_source})")
        print(f"  ⚠️  Risk Level: {intent.risk_level}/9")

        if allowed:
            if confirm:
                print(f"  🔐 REQUIRES CONFIRMATION")
            else:
                print(f"  ✅ ALLOWED - EXECUTE")
        else:
            print(f"  ❌ BLOCKED - {reason}")

        print()

    print("="*70)
    print("✅ Phase 2 Demo Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
