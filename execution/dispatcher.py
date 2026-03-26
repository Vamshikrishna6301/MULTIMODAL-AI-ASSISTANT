import ast
import operator
import time
from datetime import datetime

from core.response_model import UnifiedResponse
from execution.accessibility.accessibility_navigator import AccessibilityNavigator
from execution.adapters.windows_app import WindowsAppAdapter
from execution.adapters.windows_browser import WindowsBrowserAdapter
from execution.adapters.windows_keyboard import WindowsKeyboardAdapter
from execution.adapters.windows_file import WindowsFileAdapter
from execution.adapters.windows_system import WindowsSystemAdapter
from execution.plugin_system import get_plugin_manager
from execution.vision.vision_executor import VisionExecutor
from infrastructure.logger import get_logger


class Dispatcher:
    """
    Production Dispatcher Layer

    Responsibilities
    ----------------
    - Route approved actions
    - Delegate to correct adapter
    - Handle simple utility actions
    """

    def __init__(self):
        self.debug_logger = get_logger("execution.dispatcher")

        self.app_adapter = WindowsAppAdapter()
        self.browser_adapter = WindowsBrowserAdapter()
        self.keyboard_adapter = WindowsKeyboardAdapter()
        self.file_adapter = WindowsFileAdapter()
        self.system_adapter = WindowsSystemAdapter()
        self.plugin_manager = get_plugin_manager()
        self.accessibility = AccessibilityNavigator()

        self.vision_executor = VisionExecutor()

    def _safe_eval(self, expression: str):
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def evaluate(node):
            if isinstance(node, ast.Expression):
                return evaluate(node.body)
            if isinstance(node, ast.BinOp) and type(node.op) in operators:
                return operators[type(node.op)](evaluate(node.left), evaluate(node.right))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = evaluate(node.operand)
                return value if isinstance(node.op, ast.UAdd) else -value
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Unsafe expression")

        parsed = ast.parse(expression, mode="eval")
        return evaluate(parsed)

    # =====================================================

    def dispatch(self, decision: dict) -> UnifiedResponse:
        start_time = time.perf_counter()
        action = decision.get("action")

        try:
            target = decision.get("target")
            parameters = decision.get("parameters", {})
            self.debug_logger.debug(
                "dispatcher_entry",
                action=action,
                target=target,
            )

            # -----------------------------
            # VALIDATION
            # -----------------------------

            if not action:
                return UnifiedResponse.error_response(
                    category="execution",
                    spoken_message="Invalid action request.",
                    error_code="INVALID_ACTION"
                )

            # =====================================================
            # GET_TIME
            # =====================================================

            if action == "GET_TIME":

                now = datetime.now().strftime("%I:%M %p")

                return UnifiedResponse.success_response(
                    category="utility",
                    spoken_message=f"The current time is {now}."
                )

            # =====================================================
            # CALCULATE
            # =====================================================

            if action == "CALCULATE":

                expression = parameters.get("expression")

                if not expression:
                    return UnifiedResponse.error_response(
                        category="utility",
                        spoken_message="No expression provided.",
                        error_code="NO_EXPRESSION"
                    )

                try:

                    result = self._safe_eval(expression)

                    return UnifiedResponse.success_response(
                        category="utility",
                        spoken_message=f"The result is {result}."
                    )

                except Exception:

                    return UnifiedResponse.error_response(
                        category="utility",
                        spoken_message="Calculation failed.",
                        error_code="CALCULATION_ERROR"
                    )

            # =====================================================
            # OPEN APP
            # =====================================================

            if action == "OPEN_APP":

                browser_keywords = {"chrome", "browser", "edge", "firefox"}

                try:

                    if target and target.lower() in browser_keywords:
                        return self.browser_adapter.open_browser()

                    return self.app_adapter.open_app(target)

                except Exception as e:

                    return UnifiedResponse.error_response(
                        category="execution",
                        spoken_message="Application launch failed.",
                        error_code="APP_LAUNCH_ERROR",
                        technical_message=str(e)
                    )

            # =====================================================
            # SEARCH
            # =====================================================

            if action == "SEARCH":

                try:
                    return self.browser_adapter.search(target)

                except Exception as e:

                    return UnifiedResponse.error_response(
                        category="execution",
                        spoken_message="Search failed.",
                        error_code="SEARCH_ERROR",
                        technical_message=str(e)
                    )

            # =====================================================
            # TYPE TEXT
            # =====================================================

            if action == "TYPE_TEXT":

                try:
                    return self.keyboard_adapter.type_text(target)

                except Exception as e:

                    return UnifiedResponse.error_response(
                        category="execution",
                        spoken_message="Typing failed.",
                        error_code="TYPE_ERROR",
                        technical_message=str(e)
                    )

            # =====================================================
            # FILE OPERATIONS
            # =====================================================

            if action == "FILE_OPERATION":

                try:
                    return self.file_adapter.handle(decision)

                except Exception as e:

                    return UnifiedResponse.error_response(
                        category="execution",
                        spoken_message="File operation failed.",
                        error_code="FILE_ERROR",
                        technical_message=str(e)
                    )

            # =====================================================
            # SYSTEM COMMANDS
            # =====================================================

            if action == "SYSTEM_CONTROL":

                try:
                    return self.system_adapter.handle(decision)

                except Exception as e:

                    return UnifiedResponse.error_response(
                        category="execution",
                        spoken_message="System command failed.",
                        error_code="SYSTEM_ERROR",
                        technical_message=str(e)
                    )

            # =====================================================
            # ACCESSIBILITY
            # =====================================================

            if action == "NEXT_ITEM":
                message = self.accessibility.next_item()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            if action == "PREVIOUS_ITEM":
                message = self.accessibility.previous_item()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            if action == "READ_CURRENT":
                message = self.accessibility.read_current()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            if action == "READ_SCREEN":
                message = self.accessibility.read_screen()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            if action == "DESCRIBE_CONTEXT":
                message = self.accessibility.describe_context()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            if action == "FOCUS_INPUT":
                message = self.accessibility.focus_input()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            if action in {"ACTIVATE", "ACTIVATE_ITEM"}:
                message = self.accessibility.activate()
                return UnifiedResponse.success_response(
                    category="accessibility",
                    spoken_message=message
                )

            # =====================================================
            # VISION
            # =====================================================

            if action in {
                "START_SCENE_UNDERSTANDING",
                "STOP_SCENE_UNDERSTANDING",
                "QUERY_OBJECT",
                "VISION",
            }:

                try:
                    return self.vision_executor.handle(decision)

                except Exception as e:

                    return UnifiedResponse.error_response(
                        category="execution",
                        spoken_message="Vision system failed.",
                        error_code="VISION_ERROR",
                        technical_message=str(e)
                    )

            # =====================================================
            # PLUGINS
            # =====================================================

            if action == "PLUGIN":
                return self.plugin_manager.dispatch(decision)

            # =====================================================
            # FALLBACK
            # =====================================================

            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="Unsupported execution action.",
                error_code="UNSUPPORTED_ACTION"
            )
        finally:
            latency = (time.perf_counter() - start_time) * 1000
            self.debug_logger.debug(
                "dispatcher_exit",
                action=action,
                latency_ms=round(latency, 2),
            )
