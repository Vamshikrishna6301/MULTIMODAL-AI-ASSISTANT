"""
Safety Engine - Phase 2 Production Hardened

Unifies:
- Parser risk scoring
- IntentType-based policy rules
- Pattern escalation
- Confirmation logic
- Blocking logic

Does NOT overwrite parser risk blindly.
"""

import re
from typing import Dict

from .intent_schema import Intent, Mode, IntentType


class SafetyEngine:

    def __init__(self):

        # IntentType-based baseline risk
        self.intent_risk_policy: Dict[IntentType, int] = {
            IntentType.FILE_OPERATION: 7,
            IntentType.SYSTEM_CONTROL: 8,
            IntentType.OPEN_APP: 2,
            IntentType.SEARCH: 1,
            IntentType.TYPE_TEXT: 1,
        }

        # Pattern escalation
        self.danger_patterns = [
            r"delete all",
            r"format",
            r"remove system",
            r"shutdown now",
            r"wipe",
            r"all files",
        ]

        # Hard block threshold
        self.block_threshold = 9

        # Confirmation threshold
        self.confirmation_threshold = 6

    # =====================================================

    def evaluate(self, intent: Intent, current_mode: Mode) -> Intent:
        """
        Evaluate safety without destroying parser logic.
        """

        # -------------------------------------------------
        # Mode-based blocking
        # -------------------------------------------------
        if current_mode == Mode.DISABLED:
            intent.blocked_reason = "Assistant is disabled"
            intent.risk_level = 9
            return intent

        # -------------------------------------------------
        # Baseline policy risk (do NOT override higher risk)
        # -------------------------------------------------
        policy_risk = self.intent_risk_policy.get(intent.intent_type, 1)
        intent.risk_level = max(intent.risk_level, policy_risk)

        # -------------------------------------------------
        # Pattern-based escalation
        # -------------------------------------------------
        for pattern in self.danger_patterns:
            if re.search(pattern, intent.text.lower()):
                intent.risk_level = max(intent.risk_level, 8)
                intent.context["danger_pattern_detected"] = pattern

        # -------------------------------------------------
        # Blocking rule
        # -------------------------------------------------
        if intent.risk_level >= self.block_threshold:
            intent.blocked_reason = "Operation blocked due to extreme risk"
            intent.requires_confirmation = False
            return intent

        # -------------------------------------------------
        # Confirmation rule
        # -------------------------------------------------
        if intent.risk_level >= self.confirmation_threshold:
            intent.requires_confirmation = True

        return intent