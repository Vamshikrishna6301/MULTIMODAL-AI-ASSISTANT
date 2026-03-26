from execution.accessibility.nvda_reader import NVDAReader


class DummyElement:
    def __init__(self, name, role):
        self.name = name
        self.control_type = role


def test_nvda_reader_builds_grouped_summary_without_nvda():
    reader = NVDAReader()
    reader.controller.dll = None

    result = reader.read_screen(
        window_name="Chrome",
        elements=[
            DummyElement("Search", "Edit"),
            DummyElement("Sign in", "Button"),
            DummyElement("About", "Hyperlink"),
            DummyElement("Search", "Edit"),
        ],
        focused_element=DummyElement("Search", "Edit"),
    )

    assert "In Chrome." in result.spoken_message
    assert "Focused input field: Search." in result.spoken_message
    assert "1 button: Sign in." in result.spoken_message
    assert result.metadata["nvda_available"] is False


def test_nvda_reader_reuses_cached_summary_for_same_state():
    reader = NVDAReader()
    reader.controller.dll = None
    elements = [DummyElement("Submit", "Button")]

    first = reader.read_screen(window_name="Form", elements=elements)
    second = reader.read_screen(window_name="Form", elements=elements)

    assert first.spoken_message == second.spoken_message
    assert second.used_cache is True


def test_nvda_reader_reads_focused_element():
    reader = NVDAReader()
    reader.controller.dll = None

    result = reader.read_focused_element(
        window_name="Explorer",
        focused_element=DummyElement("Downloads", "ListItem"),
        context_label="Next item",
    )

    assert result.spoken_message == "Next item. interactive element: Downloads"
