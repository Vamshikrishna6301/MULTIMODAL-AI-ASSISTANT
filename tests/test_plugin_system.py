from core.intent_parser import IntentParser
from execution.plugin_system import get_plugin_manager
from execution.dispatcher import Dispatcher


def test_plugin_manager_loads_system_status_plugin():
    manager = get_plugin_manager()
    plugins = manager.list_plugins()

    assert any(plugin["plugin_id"] == "system_status" for plugin in plugins)


def test_intent_parser_recognizes_plugin_command():
    parser = IntentParser()
    intent = parser.parse("system status")

    assert intent.action == "PLUGIN"
    assert intent.parameters["plugin_id"] == "system_status"


def test_dispatcher_routes_plugin_action():
    dispatcher = Dispatcher()
    response = dispatcher.dispatch(
        {
            "action": "PLUGIN",
            "parameters": {"plugin_id": "system_status", "plugin_action": "default"},
        }
    )

    assert response.category == "plugin"
