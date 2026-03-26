from enum import Enum, auto
import threading
import time


class AssistantState(Enum):
    IDLE = auto()
    LISTENING = auto()
    EXECUTING = auto()
    SPEAKING = auto()
    SHUTTING_DOWN = auto()


class AssistantRuntime:

    def __init__(self):

        self._lock = threading.Lock()

        self.running = True
        self.state = AssistantState.LISTENING

        # speaking fast flag (no locking needed for reads)
        self._speaking_flag = False

        # confirmation
        self.awaiting_confirmation = False
        self.pending_intent = None

        self.interrupted = False
        self._listening_blocked_until = 0.0
        self._last_user_activity_at = 0.0
        self.focus_listener = None

    # =====================================================
    # STATE
    # =====================================================

    def set_state(self, new_state: AssistantState):
        with self._lock:
            self.state = new_state

    def get_state(self) -> AssistantState:
        with self._lock:
            return self.state

    # =====================================================
    # CONFIRMATION
    # =====================================================

    def set_confirmation(self, intent):
        with self._lock:
            self.pending_intent = intent
            self.awaiting_confirmation = True

    def clear_confirmation(self):
        with self._lock:
            self.pending_intent = None
            self.awaiting_confirmation = False

    def is_awaiting_confirmation(self) -> bool:
        with self._lock:
            return self.awaiting_confirmation

    # =====================================================
    # SPEAKING
    # =====================================================

    def start_speaking(self):
        with self._lock:
            self.state = AssistantState.SPEAKING
            self._speaking_flag = True

    def stop_speaking(self):
        with self._lock:
            self.state = AssistantState.LISTENING
            self._speaking_flag = False

    def is_speaking(self) -> bool:
        with self._lock:
            return self._speaking_flag

    def block_listening(self, duration_seconds: float):
        with self._lock:
            self._listening_blocked_until = max(
                self._listening_blocked_until,
                time.monotonic() + max(0.0, duration_seconds),
            )

    def is_listening_blocked(self) -> bool:
        with self._lock:
            return time.monotonic() < self._listening_blocked_until

    def mark_user_activity(self):
        with self._lock:
            self._last_user_activity_at = time.monotonic()

    def seconds_since_user_activity(self) -> float:
        with self._lock:
            if not self._last_user_activity_at:
                return float("inf")
            return max(0.0, time.monotonic() - self._last_user_activity_at)

    # =====================================================
    # EXECUTION
    # =====================================================

    def start_execution(self):
        with self._lock:
            self.state = AssistantState.EXECUTING
            self.interrupted = False
            focus_listener = self.focus_listener

        if focus_listener:
            try:
                focus_listener.pause()
            except Exception:
                pass

    def finish_execution(self):
        with self._lock:
            self.state = AssistantState.LISTENING
            focus_listener = self.focus_listener

        if focus_listener:
            try:
                focus_listener.resume()
            except Exception:
                pass

    def is_executing(self):
        with self._lock:
            return self.state == AssistantState.EXECUTING

    def is_listening(self):
        return self.state == AssistantState.LISTENING

    # =====================================================
    # INTERRUPT
    # =====================================================

    def request_interrupt(self):
        with self._lock:
            self.interrupted = True
            self._listening_blocked_until = max(
                self._listening_blocked_until,
                time.monotonic() + 0.25,
            )

    def clear_interrupt(self):
        with self._lock:
            self.interrupted = False

    # =====================================================
    # SHUTDOWN
    # =====================================================

    def stop(self):
        with self._lock:
            self.state = AssistantState.SHUTTING_DOWN
            self.running = False
