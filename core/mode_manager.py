"""
Mode Manager - Phase 2 Production Upgrade

Enhanced FSM with:
- Confirmation waiting state
- Intent-based execution validation
- Timeout tracking
- Safer transition logic
"""

import time
from enum import Enum
from typing import Optional, Callable, Dict, List

from .intent_schema import Mode, Intent, IntentType


class ExtendedMode(Enum):
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"


class ModeTransition:
    def __init__(self, from_mode: Mode, to_mode: Mode, trigger: str):
        self.from_mode = from_mode
        self.to_mode = to_mode
        self.trigger = trigger


class ModeManager:

    def __init__(self):
        self.current_mode = Mode.LISTENING
        self.previous_mode = Mode.LISTENING

        self.transition_history: List[tuple] = []
        self.callbacks: Dict[Mode, List[Callable]] = {mode: [] for mode in Mode}

        self.max_history = 100

        # Confirmation handling
        self.waiting_for_confirmation = False
        self.pending_intent: Optional[Intent] = None
        self.confirmation_timeout = 10  # seconds
        self.confirmation_timestamp = 0.0

        self.transitions = self._define_transitions()

    # =========================================================
    # PUBLIC API
    # =========================================================

    def handle_intent(self, intent: Intent) -> Optional[Intent]:
        """
        Main entry point for Phase 2 control logic.
        Decides if intent should execute, wait, or be blocked.
        """

        # 1️⃣ Confirmation flow
        if self.waiting_for_confirmation:
            return self._handle_confirmation(intent)

        # 2️⃣ Dangerous intent
        if intent.requires_confirmation:
            self._enter_confirmation_state(intent)
            return None  # execution paused

        # 3️⃣ Mode switching
        self._auto_transition(intent)

        # 4️⃣ Execution permission check
        if not self.can_execute_intent(intent):
            intent.blocked_reason = "Mode does not allow execution"
            return intent

        return intent

    def set_mode(self, new_mode: Mode, reason: str = "unknown") -> bool:

        if not self._can_transition(self.current_mode, new_mode):
            return False

        self.previous_mode = self.current_mode
        self.current_mode = new_mode
        self.transition_history.append((self.previous_mode, new_mode, reason))

        if len(self.transition_history) > self.max_history:
            self.transition_history.pop(0)

        self._execute_callbacks(new_mode)
        return True

    def get_mode(self) -> Mode:
        return self.current_mode

    def is_enabled(self) -> bool:
        return self.current_mode != Mode.DISABLED

    # =========================================================
    # CONFIRMATION HANDLING
    # =========================================================

    def _enter_confirmation_state(self, intent: Intent):
        self.waiting_for_confirmation = True
        self.pending_intent = intent
        self.confirmation_timestamp = time.time()

    def _handle_confirmation(self, intent: Intent) -> Optional[Intent]:

        # Timeout
        if time.time() - self.confirmation_timestamp > self.confirmation_timeout:
            self._reset_confirmation()
            return None

        response = intent.text.lower().strip()

        if response in ["yes", "confirm", "do it"]:
            confirmed_intent = self.pending_intent
            self._reset_confirmation()
            if confirmed_intent is not None:
                confirmed_intent.confirmed = True
                confirmed_intent.requires_confirmation = False
            return confirmed_intent

        elif response in ["no", "cancel", "stop"]:
            self._reset_confirmation()
            return None

        return None  # still waiting

    def _reset_confirmation(self):
        self.waiting_for_confirmation = False
        self.pending_intent = None
        self.confirmation_timestamp = 0.0

    # =========================================================
    # EXECUTION CONTROL
    # =========================================================

    def can_execute_intent(self, intent: Intent) -> bool:

        if intent.intent_type == IntentType.UNKNOWN:
            return False

        if self.current_mode == Mode.DISABLED:
            return False

        if self.current_mode == Mode.DICTATION and intent.intent_type != IntentType.TYPE_TEXT:
            return False

        if self.current_mode == Mode.QUESTION and intent.intent_type != IntentType.QUESTION:
            return False

        return True

    # =========================================================
    # AUTO MODE TRANSITION
    # =========================================================

    def _auto_transition(self, intent: Intent):

        if intent.intent_type == IntentType.QUESTION:
            self.set_mode(Mode.QUESTION, "question_detected")

        elif intent.intent_type == IntentType.DICTATION:
            self.set_mode(Mode.DICTATION, "dictation_mode_enabled")

        else:
            self.set_mode(Mode.COMMAND, "command_detected")

    # =========================================================
    # FSM DEFINITION
    # =========================================================

    def _define_transitions(self) -> List[ModeTransition]:

        return [
            ModeTransition(Mode.LISTENING, Mode.COMMAND, "command_detected"),
            ModeTransition(Mode.LISTENING, Mode.QUESTION, "question_detected"),
            ModeTransition(Mode.LISTENING, Mode.DICTATION, "dictation_mode_enabled"),
            ModeTransition(Mode.LISTENING, Mode.DISABLED, "disable_command"),

            ModeTransition(Mode.COMMAND, Mode.LISTENING, "command_completed"),
            ModeTransition(Mode.COMMAND, Mode.DICTATION, "switch_to_dictation"),
            ModeTransition(Mode.COMMAND, Mode.DISABLED, "disable_command"),

            ModeTransition(Mode.DICTATION, Mode.LISTENING, "exit_dictation"),
            ModeTransition(Mode.DICTATION, Mode.COMMAND, "switch_to_command"),
            ModeTransition(Mode.DICTATION, Mode.DISABLED, "disable_command"),

            ModeTransition(Mode.QUESTION, Mode.LISTENING, "question_answered"),
            ModeTransition(Mode.QUESTION, Mode.COMMAND, "switch_to_command"),
            ModeTransition(Mode.QUESTION, Mode.DISABLED, "disable_command"),

            ModeTransition(Mode.DISABLED, Mode.LISTENING, "enable_assistant"),
        ]

    def _can_transition(self, from_mode: Mode, to_mode: Mode) -> bool:

        if from_mode == to_mode:
            return False

        for transition in self.transitions:
            if transition.from_mode == from_mode and transition.to_mode == to_mode:
                return True
        return False

    def _execute_callbacks(self, mode: Mode) -> None:
        for callback in self.callbacks.get(mode, []):
            try:
                callback(mode)
            except Exception:
                pass
