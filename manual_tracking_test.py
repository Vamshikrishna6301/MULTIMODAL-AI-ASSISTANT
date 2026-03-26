from execution.vision.event_engine import EventEngine

engine = EventEngine()

events = [
    {
        "type": "ENTRY",
        "object": {
            "id": 1,
            "label": "person"
        }
    }
]

print(engine.process_events(events))