from __future__ import annotations

import queue
from typing import Any, Dict, List, Optional

try:
    import pythoncom
except Exception:  # pragma: no cover
    pythoncom = None

try:
    import win32gui
except Exception:  # pragma: no cover
    win32gui = None

try:
    from pywinauto import Application, Desktop
except Exception:  # pragma: no cover
    Application = None
    Desktop = None

from execution.accessibility.uia_focus import get_focused_window


INTERACTIVE_TYPES = {
    "Button",
    "MenuItem",
    "Edit",
    "CheckBox",
    "ComboBox",
    "ListItem",
    "TabItem",
    "Document",
    "TreeItem",
}


def _safe_name(element: Any) -> str:
    try:
        text = element.window_text()
        if text:
            return text
    except Exception:
        pass
    try:
        return (
            element.window_text()
            or element.element_info.class_name
            or "Unnamed"
        )
    except Exception:
        return "Unknown"


def _safe_role(element: Any) -> str:
    try:
        return element.friendly_class_name()
    except Exception:
        return "Element"


def _safe_automation_id(element: Any) -> str:
    try:
        return element.element_info.automation_id or ""
    except Exception:
        return ""


def _safe_rect(element: Any):
    try:
        rect = element.rectangle()
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        return None


def _serialize_element(element: Any, *, index: int = -1) -> Dict[str, Any]:
    role = _safe_role(element)
    name = _safe_name(element)
    automation_id = _safe_automation_id(element)
    bbox = _safe_rect(element)
    return {
        "index": index,
        "name": name,
        "role": role,
        "control_type": role,
        "automation_id": automation_id,
        "bounding_rect": bbox,
        "region": None,
        "locator": {
            "name": name,
            "role": role,
            "automation_id": automation_id,
            "bounding_rect": bbox,
        },
    }


def _active_hwnd() -> Optional[int]:
    if win32gui is None:
        return None
    try:
        return win32gui.GetForegroundWindow()
    except Exception:
        return None


def _active_window():
    hwnd = _active_hwnd()
    if hwnd is None or Application is None:
        return None
    app = Application(backend="uia").connect(handle=hwnd)
    return app.window(handle=hwnd)


def _iter_children(root: Any, *, max_depth: int, max_children: int, interactive_only: bool) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    queue_items = [(root, 0)]

    while queue_items:
        element, depth = queue_items.pop(0)
        if depth >= max_depth:
            continue
        try:
            children = element.children()[:max_children]
        except Exception:
            children = []
        for child in children:
            serialized = _serialize_element(child, index=len(results))
            if (not interactive_only) or serialized["control_type"] in INTERACTIVE_TYPES:
                results.append(serialized)
            queue_items.append((child, depth + 1))
    return results


def _match_locator(element: Any, locator: Dict[str, Any]) -> bool:
    name = _safe_name(element)
    role = _safe_role(element)
    automation_id = _safe_automation_id(element)
    bbox = _safe_rect(element)
    return (
        (locator.get("automation_id") and automation_id == locator.get("automation_id"))
        or (
            name == locator.get("name")
            and role == locator.get("role")
            and (not locator.get("bounding_rect") or bbox == tuple(locator.get("bounding_rect")))
        )
    )


def _find_in_active_window(locator: Dict[str, Any]):
    root = _active_window()
    if root is None:
        return None
    queue_items = [root]
    while queue_items:
        element = queue_items.pop(0)
        if _match_locator(element, locator):
            return element
        try:
            queue_items.extend(element.children())
        except Exception:
            continue
    return None


def _handle_request(request: Dict[str, Any]):
    cmd = request.get("cmd")
    params = request.get("params") or {}

    if cmd == "get_focus":
        focused = get_focused_window()
        if focused is None:
            return None
        return _serialize_element(focused, index=-1)

    if cmd == "active_window":
        hwnd = _active_hwnd()
        if hwnd is None:
            return None
        title = ""
        if win32gui is not None:
            try:
                title = win32gui.GetWindowText(hwnd)
            except Exception:
                title = ""
        return {"hwnd": hwnd, "title": title or "Unknown window"}

    if cmd == "scan_children":
        root = _active_window()
        if root is None:
            return []
        return _iter_children(
            root,
            max_depth=int(params.get("max_depth", 3)),
            max_children=int(params.get("max_children", 30)),
            interactive_only=bool(params.get("interactive_only", False)),
        )

    if cmd == "set_focus":
        locator = params.get("locator") or {}
        element = _find_in_active_window(locator)
        if element is None:
            return None
        element.set_focus()
        return True

    if cmd == "invoke":
        locator = params.get("locator") or {}
        element = _find_in_active_window(locator)
        if element is None:
            return None
        try:
            element.invoke()
        except Exception:
            element.click_input()
        return True

    return None


def worker_main(input_queue, output_queue):
    if pythoncom is not None:
        pythoncom.CoInitialize()
    try:
        while True:
            try:
                request = input_queue.get()
            except (EOFError, KeyboardInterrupt):
                break
            if not isinstance(request, dict):
                continue
            request_id = request.get("id")
            if request.get("cmd") == "__stop__":
                output_queue.put({"id": request_id, "result": True})
                break
            try:
                result = _handle_request(request)
            except Exception:
                result = None
            try:
                output_queue.put({"id": request_id, "result": result})
            except Exception:
                pass
    finally:
        if pythoncom is not None:
            pythoncom.CoUninitialize()
