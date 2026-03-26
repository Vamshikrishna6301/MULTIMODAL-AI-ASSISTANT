from execution.accessibility.navigation_orchestrator import (
    NavigationCommand,
    NavigationOrchestrator,
    NavigationSnapshotCache,
)
from execution.accessibility.navigation_state import NavigationState


class DummyElement:
    def __init__(self, name, role, region=None):
        self.name = name
        self.role = role
        self.control_type = role
        self.region = region
        self.focused = False
        self.clicked = False

    def speakable(self):
        return f"{self.role}: {self.name}"

    def set_focus(self):
        self.focused = True

    def click(self):
        self.clicked = True

    def is_button(self):
        return self.role.lower() == "button"

    def is_input(self):
        return self.role.lower() in {"edit", "input"}

    def is_link(self):
        return self.role.lower() == "hyperlink"


def test_scan_strategy_builds_snapshot_and_speech():
    elements = [DummyElement("Search", "Edit"), DummyElement("Submit", "Button")]
    orchestrator = NavigationOrchestrator(
        state=NavigationState(),
        cache=NavigationSnapshotCache(ttl_seconds=5),
        window_provider=lambda: "Demo Window",
        focus_provider=lambda: elements[0],
        scanner=lambda: ("Demo Window", elements),
        announcer=lambda text: text,
    )

    result = orchestrator.execute(NavigationCommand(action="read_screen"))

    assert result.success
    assert result.strategy == "scan"
    assert "Demo Window" in result.spoken_message
    assert len(result.elements) == 2
    assert result.confidence >= 0.8


def test_focus_strategy_activates_focused_element_without_scan():
    focused = DummyElement("Save", "Button")
    orchestrator = NavigationOrchestrator(
        state=NavigationState(),
        window_provider=lambda: "Editor",
        focus_provider=lambda: focused,
        scanner=lambda: ("Editor", []),
        announcer=lambda text: text,
    )

    result = orchestrator.execute(NavigationCommand(action="activate"))

    assert result.success
    assert result.strategy == "focus"
    assert focused.clicked is True
    assert "Activated" in result.spoken_message


def test_keyboard_strategy_uses_cached_snapshot_when_focus_missing():
    elements = [DummyElement("First", "Button"), DummyElement("Second", "Button")]
    state = NavigationState()
    cache = NavigationSnapshotCache(ttl_seconds=5)
    orchestrator = NavigationOrchestrator(
        state=state,
        cache=cache,
        window_provider=lambda: "Browser",
        focus_provider=lambda: None,
        scanner=lambda: ("Browser", elements),
        announcer=lambda text: text,
    )

    orchestrator.refresh()
    result = orchestrator.execute(NavigationCommand(action="next"))

    assert result.success
    assert result.strategy == "keyboard"
    assert result.element.name in {"First", "Second"}


def test_semantic_navigation_wraps_to_matching_input():
    elements = [
        DummyElement("Open", "Button"),
        DummyElement("Search box", "Edit"),
        DummyElement("Help", "Hyperlink"),
    ]
    state = NavigationState()
    orchestrator = NavigationOrchestrator(
        state=state,
        cache=NavigationSnapshotCache(ttl_seconds=5),
        window_provider=lambda: "App",
        focus_provider=lambda: None,
        scanner=lambda: ("App", elements),
        announcer=lambda text: text,
    )

    orchestrator.refresh()
    result = orchestrator.execute(
        NavigationCommand(action="semantic_next", semantic_type="input")
    )

    assert result.success
    assert result.element.name == "Search box"
    assert result.element.focused is True
