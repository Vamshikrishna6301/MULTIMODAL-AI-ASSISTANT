from __future__ import annotations

import importlib.util
import inspect
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.response_model import UnifiedResponse


@dataclass
class PluginIntentMatch:
    plugin_id: str
    plugin_action: str
    confidence: float
    target: Optional[str] = None
    parameters: Dict = field(default_factory=dict)
    risk_level: int = 0
    requires_confirmation: bool = False


class AssistantPlugin:
    plugin_id = "base"
    name = "Base Plugin"
    version = "1.0"
    command_patterns: List[str] = []

    def match(self, text: str) -> Optional[PluginIntentMatch]:
        normalized = text.lower().strip()
        for pattern in self.command_patterns:
            match = re.search(pattern, normalized)
            if match:
                groups = match.groupdict()
                return PluginIntentMatch(
                    plugin_id=self.plugin_id,
                    plugin_action=groups.get("plugin_action", "default"),
                    confidence=0.9,
                    target=groups.get("target"),
                    parameters={k: v for k, v in groups.items() if v is not None},
                )
        return None

    def handle(self, decision: Dict) -> UnifiedResponse:
        return UnifiedResponse.error_response(
            category="plugin",
            spoken_message="Plugin did not implement a handler.",
            error_code="PLUGIN_NOT_IMPLEMENTED",
        )


class PluginManager:
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, AssistantPlugin] = {}
        self._loaded = False

    def ensure_loaded(self):
        if self._loaded:
            return
        self.plugins_dir.mkdir(exist_ok=True)
        self._load_plugins_from_directory()
        self._loaded = True

    def register(self, plugin: AssistantPlugin):
        self.plugins[plugin.plugin_id] = plugin

    def match_intent(self, text: str) -> Optional[PluginIntentMatch]:
        self.ensure_loaded()
        for plugin in self.plugins.values():
            try:
                match = plugin.match(text)
                if match:
                    return match
            except Exception:
                continue
        return None

    def dispatch(self, decision: Dict) -> Optional[UnifiedResponse]:
        self.ensure_loaded()
        parameters = decision.get("parameters", {}) or {}
        plugin_id = parameters.get("plugin_id")
        if not plugin_id:
            return None

        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return UnifiedResponse.error_response(
                category="plugin",
                spoken_message=f"Plugin {plugin_id} is not available.",
                error_code="PLUGIN_NOT_FOUND",
            )

        try:
            return plugin.handle(decision)
        except Exception as exc:
            return UnifiedResponse.error_response(
                category="plugin",
                spoken_message=f"Plugin {plugin_id} failed.",
                error_code="PLUGIN_EXECUTION_ERROR",
                technical_message=str(exc),
            )

    def list_plugins(self) -> List[Dict]:
        self.ensure_loaded()
        return [
            {
                "plugin_id": plugin.plugin_id,
                "name": plugin.name,
                "version": plugin.version,
            }
            for plugin in self.plugins.values()
        ]

    def _load_plugins_from_directory(self):
        for path in self.plugins_dir.glob("*_plugin.py"):
            self._load_plugin_file(path)

    def _load_plugin_file(self, path: Path):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, AssistantPlugin) and obj is not AssistantPlugin:
                try:
                    self.register(obj())
                except Exception:
                    continue


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
