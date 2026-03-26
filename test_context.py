'''from core.intent_parser import IntentParser
from core.context_memory import ContextMemory

parser = IntentParser()
memory = ContextMemory()

commands = [
    "open chrome",
    "search transformers",
    "delete report.pdf",
    "delete"
]

for cmd in commands:
    intent = parser.parse(cmd)
    intent = memory.enrich(intent)
    memory.update(intent)

    print("\nInput:", cmd)
    print("Action:", intent.action)
    print("Target:", intent.target)
    print("Context:", intent.context)

print("\nMemory Snapshot:")
print(memory.get_memory_snapshot())
'''
# mic_debug_test.py

from voice.mic_stream import MicrophoneStream

with MicrophoneStream() as mic:
    print("Listening...")
    for i in range(20):
        frame = mic.read()
        print("Frame length:", len(frame))