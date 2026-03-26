import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from core.environment_memory import EnvironmentMemory
from core.response_model import UnifiedResponse
from execution.accessibility.semantic_navigator import SemanticNavigator
from execution.dispatcher import Dispatcher
from execution.execution_hardening import ExecutionHardeningManager
from execution.execution_logger import ExecutionLogger
from execution.performance_layer import PerformanceOptimizationLayer
from execution.uia_service.uia_client import UIAClient
from infrastructure.watchdog import get_watchdog

from execution.accessibility.accessibility_navigator import AccessibilityNavigator
from execution.accessibility.perception_filter import PerceptionFilter
from infrastructure.logger import get_logger


class ExecutionEngine:
    """
    Production Execution EngineFself.tt

    Responsibilities
    ----------------
    - Validate execution decisions
    - Route actions to correct subsystem
    - Handle accessibility navigation
    - Execute UI automation commands
    - Maintain context memory
    - Log execution activity
    """

    UIA_RETRIES = 2

    # =====================================================

    def __init__(self, context_memory):
        self.debug_logger = get_logger("execution.executor")

        self.context_memory = context_memory
        self.environment_memory = EnvironmentMemory()

        # Core subsystems
        self.dispatcher = Dispatcher()
        self.dispatcher.vision_executor.camera_detector.environment_memory = self.environment_memory
        self.logger = ExecutionLogger()
        self.hardening = ExecutionHardeningManager()
        self.performance = PerformanceOptimizationLayer()
        self.watchdog = get_watchdog()
        self.watchdog.register("execution_engine", timeout_seconds=15.0)

        # UI Automation
        self.uia_client = UIAClient()

        # Accessibility perception
        self.perception_filter = PerceptionFilter()

        # Accessibility navigation
        self.navigator = AccessibilityNavigator(
            self.uia_client,
            self.dispatcher.vision_executor
        )
        self.semantic_nav = SemanticNavigator(self.navigator.state)

    # =====================================================
    # MAIN EXECUTION
    # =====================================================

    def execute(self, decision: dict) -> UnifiedResponse:

        try:
            started = time.perf_counter()
            self.debug_logger.debug(
                "executor_start",
                action=decision.get("action") if isinstance(decision, dict) else None,
                status=decision.get("status") if isinstance(decision, dict) else None,
            )
            self.watchdog.heartbeat("execution_engine")

            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if not isinstance(decision, dict):
                return self._error("Invalid execution request.", "INVALID_DECISION")

            if decision.get("status") != "APPROVED":
                return self._error("Execution blocked.", "NOT_APPROVED")

            if decision.get("blocked_reason"):
                return self._error("Blocked by safety system.", "BLOCKED_BY_SAFETY")

            action = decision.get("action")

            if not action:
                return self._error("No executable action found.", "MISSING_ACTION")

            cached_response = self.performance.get_cached_response(decision)
            if cached_response:
                cached_response.metadata = dict(cached_response.metadata or {})
                cached_response.metadata["cache_hit"] = True
                return cached_response

            # ------------------------------------------------
            # RISK VALIDATION
            # ------------------------------------------------

            risk_level = decision.get("risk_level", 0)
            requires_confirmation = decision.get("requires_confirmation", False)
            confirmed = decision.get("confirmed", False)

            if (requires_confirmation or risk_level >= 7) and not confirmed:
                return self._error(
                    "Execution requires confirmation.",
                    "CONFIRMATION_REQUIRED"
                )

            # =================================================
            # CONVERSATION HANDLING
            # =================================================

            if action == "GREETING":

                response = UnifiedResponse.success_response(
                    category="conversation",
                    spoken_message="Hello. How can I help you?"
                )

            # =================================================
            # ACCESSIBILITY NAVIGATION
            # =================================================

            elif action == "READ_SCREEN":
                response = self._handle_read_screen()

            elif action == "READ_CURRENT":
                response = self._handle_read_current()

            elif action == "DESCRIBE_CONTEXT":
                response = self._handle_describe_context()

            elif action == "NEXT_ITEM":
                response = self._nav(self.navigator.next_item)

            elif action == "PREVIOUS_ITEM":
                response = self._nav(self.navigator.previous_item)

            elif action == "ACTIVATE_ITEM":
                response = self._nav(self.navigator.activate)

            # =================================================
            # SEMANTIC NAVIGATION
            # =================================================

            elif action == "NEXT_BUTTON":
                response = self._nav(self.navigator.next_button)

            elif action == "NEXT_INPUT":
                response = self._nav(self.navigator.next_input)

            elif action == "NEXT_LINK":
                response = self._nav(self.navigator.next_link)

            elif action == "NEXT_TAB":
                response = self._nav(self.navigator.next_tab)

            elif action == "NEXT_MENU":
                response = self._nav(self.navigator.next_menu)

            elif action == "NEXT_CHAT":
                response = self._nav(self.navigator.next_chat)

            elif action == "NEXT_MESSAGE":
                response = self._nav(self.navigator.next_message)

            elif action == "FOCUS_INPUT":
                response = self._nav(self.navigator.focus_input)

            # =================================================
            # UIA ACTIONS
            # =================================================

            elif action == "CLICK_INDEX":
                index = decision.get("parameters", {}).get("index")
                response = self._handle_click_index(index)

            elif action == "CLICK_NAME":
                name = decision.get("parameters", {}).get("name")
                response = self._handle_click_name(name)

            elif action == "FOCUS_NAME":
                name = decision.get("parameters", {}).get("name")
                response = self._handle_focus_name(name)

            elif action == "START_SCENE_UNDERSTANDING":
                response = self._handle_scene_understanding()

            elif action == "STOP_SCENE_UNDERSTANDING":
                response = self._handle_stop_scene_understanding()

            elif action == "QUERY_OBJECT":

                obj = decision["parameters"]["object"]
                spoken_obj = self.environment_memory._normalize(obj)

                data = self.environment_memory.query(obj)

                if not data:
                    response = UnifiedResponse.success_response(
                        category="vision",
                        spoken_message=f"I cannot locate the {spoken_obj}."
                    )
                else:
                    spoken_position = self._describe_relative_position(data)
                    response = UnifiedResponse.success_response(
                        category="vision",
                        spoken_message=f"The {spoken_obj} is {spoken_position}."
                    )

            # =================================================
            # DISPATCHER ROUTING
            # =================================================

            else:

                response = self._execute_hardened(
                    action,
                    self._dispatcher_operation(decision),
                    rollback=self._rollback_for(action, decision),
                )

                if getattr(response, "success", False):
                    self._safe_update_context(decision)

            # ------------------------------------------------
            # LOGGING + SPEECH
            # ------------------------------------------------

            trace_id = self.logger.log(decision, response)
            response.metadata = dict(response.metadata or {})
            response.metadata.setdefault("trace_id", trace_id)
            response.metadata.setdefault(
                "execution_duration_ms",
                round(self.performance.record_timing(action, started), 2)
            )
            self.performance.store_response(decision, response)
            self.watchdog.heartbeat("execution_engine")

            if response.spoken_message:
                response.metadata["tts_handled"] = False

            self.debug_logger.debug(
                "executor_end",
                action=action,
                success=getattr(response, "success", False),
                speech_length=len(getattr(response, "spoken_message", "") or ""),
            )

            return response

        except Exception as e:

            print("🔥 EXECUTION EXCEPTION:", repr(e))

            return self._error(
                "An internal execution error occurred.",
                "EXECUTION_FAILURE",
                technical=str(e)
            )

    # =====================================================
    # NAVIGATION WRAPPER
    # =====================================================

    def _nav(self, func):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(func)
            speech = future.result(timeout=0.5)
        except TimeoutError:
            return UnifiedResponse.success_response(
                category="accessibility",
                spoken_message="Navigation is still in progress.",
                metadata={"navigation_async": True}
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        return UnifiedResponse.success_response(
            category="accessibility",
            spoken_message=speech,
            metadata=self.navigator.consume_metadata()
        )

    # =====================================================
    # READ SCREEN
    # =====================================================

    def _handle_read_screen(self):
        self.debug_logger.debug("executor_read_screen_start")
        speech = self.navigator.read_screen()
        speech = (speech or "").strip() or "No readable content found."
        self.debug_logger.debug("executor_read_screen_end", speech_length=len(speech))

        return UnifiedResponse.success_response(
            category="accessibility",
            spoken_message=speech,
            metadata=self.navigator.consume_metadata()
        )

    def _handle_read_current(self):

        speech = self.navigator.read_current()

        return UnifiedResponse.success_response(
            category="accessibility",
            spoken_message=speech,
            metadata=self.navigator.consume_metadata()
        )

    def _handle_describe_context(self):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self.navigator.describe_context)
            speech = future.result(timeout=1.5)
        except TimeoutError:
            speech = "You are on the current screen."
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        return UnifiedResponse.success_response(
            category="accessibility",
            spoken_message=speech,
            metadata=self.navigator.consume_metadata()
        )

    def _handle_scene_understanding(self):

        detector = self.dispatcher.vision_executor.camera_detector

        try:
            objects = detector.detect_objects()

            if not objects:
                return UnifiedResponse.success_response(
                    category="vision",
                    spoken_message="I cannot see any objects clearly."
                )

            speech = self.dispatcher.vision_executor.scene_reasoner.describe_scene(objects)

            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=speech
            )

        except Exception as e:
            return self._error(
                "Camera could not start.",
                "CAMERA_FAILED",
                technical=str(e)
            )

    def _handle_stop_scene_understanding(self):

        detector = self.dispatcher.vision_executor.camera_detector

        try:
            detector.stop()

            return UnifiedResponse.success_response(
                category="vision",
                spoken_message="Camera stopped."
            )

        except Exception as e:
            return self._error(
                "Camera could not stop.",
                "CAMERA_STOP_FAILED",
                technical=str(e)
            )

    def _execute_hardened(self, action: str, operation, rollback=None):
        self.watchdog.heartbeat("execution_engine")
        result = self.hardening.execute(action, operation, rollback=rollback)
        self.watchdog.heartbeat("execution_engine")
        response = result.response
        response.metadata = dict(response.metadata or {})
        response.metadata["rollback_attempted"] = result.rollback_attempted
        response.metadata["rollback_succeeded"] = result.rollback_succeeded
        return response

    def _dispatcher_operation(self, decision):

        def operation():
            response = self.dispatcher.dispatch(decision)

            if not response:
                return self._error(
                    "Unsupported execution action.",
                    "UNSUPPORTED_ACTION"
                )

            return response

        return operation

    def _rollback_for(self, action: str, decision: dict):

        if action == "TYPE_TEXT":
            return self._rollback_typed_text

        if action == "OPEN_APP":
            target = decision.get("target")
            return lambda: self._rollback_open_app(target)

        return None

    def _rollback_typed_text(self):

        try:
            adapter = self.dispatcher.keyboard_adapter

            if hasattr(adapter, "undo_last_input"):
                return bool(adapter.undo_last_input())

        except Exception:
            return False

        return False

    def _rollback_open_app(self, target):

        if not target:
            return False

        try:
            response = self.dispatcher.system_adapter.close_application(target)
            return bool(getattr(response, "success", False))

        except Exception:
            return False

    # =====================================================
    # UIA HANDLERS
    # =====================================================

    def _handle_click_index(self, index):

        if not isinstance(index, int) or index <= 0:
            return self._error("Invalid selection number.", "INVALID_INDEX")

        result, attempts = self._uia_call(self.uia_client.click_index, index)

        if not isinstance(result, dict):
            return self._error(
                "UIA service unavailable.",
                "UIA_ERROR",
                technical=f"attempts={attempts}"
            )

        if result.get("status") != "success":
            return self._error(
                result.get("message", "Click failed."),
                "CLICK_FAILED"
            )

        return UnifiedResponse.success_response(
            category="execution",
            spoken_message=result.get("message"),
            metadata={"attempt_count": attempts}
        )

    def _handle_click_name(self, name):

        if not name or not isinstance(name, str):
            return self._error("Invalid element name.", "INVALID_NAME")

        tree = self.navigator.get_accessibility_tree()
        target = self.semantic_nav.find_element_by_name(
            getattr(tree, "elements", []) or [],
            name,
        )

        if target:
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(target.click)
                future.result(timeout=2)
                self.debug_logger.info(
                    "ELEMENT_MATCHED",
                    target=name,
                    matched_name=getattr(target, "name", name),
                )
                self.debug_logger.info(
                    "ELEMENT_CLICKED",
                    target=name,
                    matched_name=getattr(target, "name", name),
                )
                return UnifiedResponse.success_response(
                    category="execution",
                    spoken_message=f"Clicked {getattr(target, 'name', name)}.",
                    metadata={"click_fallback": "navigator_direct"},
                )
            except TimeoutError:
                future.cancel()
                return self._error(
                    "Element could not be activated.",
                    "CLICK_TIMEOUT",
                )
            except Exception as exc:
                self.debug_logger.warning(
                    "element_click_direct_failed",
                    target=name,
                    matched_name=getattr(target, "name", name),
                    error=str(exc),
                )
                return self._fallback_click_name(name)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        return UnifiedResponse.success_response(
            category="execution",
            spoken_message="I couldn't find that control on the screen."
        )

    def _handle_focus_name(self, name):

        if not name or not isinstance(name, str):
            return self._error("Invalid element name.", "INVALID_NAME")

        tree = self.navigator.get_accessibility_tree()
        target = self.semantic_nav.find_element_by_name(
            getattr(tree, "elements", []) or [],
            name,
        )

        if not target:
            return UnifiedResponse.success_response(
                category="accessibility",
                spoken_message=f"I cannot find {name}."
            )

        try:
            target.set_focus()
            self.navigator.state.set_focused(target)
            return UnifiedResponse.success_response(
                category="accessibility",
                spoken_message=f"Focused {getattr(target, 'name', name)}."
            )
        except Exception as exc:
            return self._error(
                "Focus failed.",
                "FOCUS_FAILED",
                technical=str(exc),
            )

    def _fallback_click_name(self, name: str) -> UnifiedResponse:
        tree = self.navigator.get_accessibility_tree()
        target = self.semantic_nav.find_element_by_name(
            getattr(tree, "elements", []) or [],
            name,
        )
        if not target:
            return UnifiedResponse.success_response(
                category="execution",
                spoken_message="I couldn't find that control on the screen."
            )
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(target.click)
            future.result(timeout=2)
            self.debug_logger.info(
                "ELEMENT_CLICKED",
                target=name,
                matched_name=getattr(target, "name", name),
                path="fallback",
            )
            return UnifiedResponse.success_response(
                category="execution",
                spoken_message=f"Clicked {getattr(target, 'name', name)}.",
                metadata={"click_fallback": "navigator_state"},
            )
        except TimeoutError:
            future.cancel()
            return self._error(
                "Element could not be activated.",
                "CLICK_TIMEOUT",
            )
        except Exception as exc:
            return self._error(
                "Click failed.",
                "CLICK_FAILED",
                technical=str(exc),
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _describe_relative_position(self, data) -> str:
        bbox = data.get("bbox") or ()
        if len(bbox) != 4:
            return "in front of you"
        x1, _, x2, _ = bbox
        center_x = (x1 + x2) / 2
        if center_x < 1280 * 0.35:
            return "on your left"
        if center_x > 1280 * 0.65:
            return "on your right"
        return "in front of you"

    # =====================================================
    # UIA RETRY
    # =====================================================

    def _uia_call(self, func, *args):

        attempts = 0

        for _ in range(self.UIA_RETRIES + 1):
            attempts += 1

            result = func(*args)

            if isinstance(result, dict):
                return result, attempts

        return None, attempts

    # =====================================================
    # CONTEXT MEMORY
    # =====================================================

    def _safe_update_context(self, decision):

        try:

            action = decision.get("action")
            target = decision.get("target")

            if action == "OPEN_APP" and target:
                self.context_memory.last_app = target

            elif action == "FILE_OPERATION" and target:
                self.context_memory.last_file = target

        except Exception as e:
            print("⚠️ Context update failed:", e)

    # =====================================================
    # ERROR
    # =====================================================

    def _error(self, message, code, technical=None):

        return UnifiedResponse.error_response(
            category="execution",
            spoken_message=message,
            error_code=code,
            technical_message=technical
        )

    # =====================================================

    @property
    def camera_detector(self):
        return self.dispatcher.vision_executor.camera_detector
