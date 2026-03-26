"""
Safety Rules - Phase 2
Rule-based safety validation following OWASP and OpenAssistant patterns
Implements confirmation requirements and action blocking
"""

from typing import List, Tuple, Optional
from enum import Enum
from .intent_schema import Intent, IntentType


class RiskLevel(Enum):
    """Risk classification (OpenAssistant 0-9 scale)"""
    NONE = 0          # No risk
    LOW = 2            # Safe action
    MEDIUM = 4         # Requires context checking
    HIGH = 6           # Requires confirmation
    CRITICAL = 8       # Usually blocked
    FORBIDDEN = 9      # Always blocked


class SafetyRules:
    """
    Safety validation engine following industry standards:
    - OWASP principle: Security > convenience
    - OpenAssistant risk taxonomy
    - Home Assistant confirmation patterns
    """
    
    def __init__(self):
        self.confirmation_rules = self._build_confirmation_rules()
        self.block_rules = self._build_block_rules()
        self.acl_rules = self._build_acl_rules()
        self.override_tokens: List[str] = []
    
    def validate(self, intent: Intent) -> Tuple[bool, Optional[str], bool]:
        """
        Validate intent with safety rules
        Returns: (allowed, block_reason, requires_confirmation)
        """
        # Check if blocked
        block_reason = self._check_block_rules(intent)
        if block_reason:
            return False, block_reason, False
        
        # Check if requires confirmation
        requires_confirmation = self._check_confirmation_rules(intent)
        
        # Check ACL
        if not self._check_acl_rules(intent):
            return False, "Access control violation", False
        
        return True, None, requires_confirmation
    
    def requires_confirmation(self, intent: Intent) -> bool:
        """Check if intent requires user confirmation"""
        return self._check_confirmation_rules(intent)
    
    def is_blocked(self, intent: Intent) -> Tuple[bool, Optional[str]]:
        """Check if intent is blocked with reason"""
        reason = self._check_block_rules(intent)
        return reason is not None, reason
    
    def get_risk_assessment(self, intent: Intent) -> dict:
        """Get comprehensive risk assessment"""
        return {
            "risk_level": intent.risk_level,
            "is_blocked": self._check_block_rules(intent) is not None,
            "requires_confirmation": self._check_confirmation_rules(intent),
            "blocked_reason": self._check_block_rules(intent),
            "description": self._get_risk_description(intent),
        }
    
    # ========================= Private Methods =========================
    
    def _build_confirmation_rules(self) -> List[dict]:
        """
        Actions requiring user confirmation
        Multi-layered (Home Assistant pattern)
        """
        return [
            # Destructive operations
            {
                "action": "delete",
                "always": True,
                "reason": "Destructive operation"
            },
            {
                "action": "format",
                "always": True,
                "reason": "Permanent data loss"
            },
            {
                "action": "uninstall",
                "always": True,
                "reason": "System modification"
            },
            
            # System changes
            {
                "action": "disable",
                "always": True,
                "reason": "System state change"
            },
            {
                "action": "shutdown",
                "always": True,
                "reason": "System termination"
            },
            
            # Risk-based (medium confidence = confirm)
            {
                "action": "open",
                "condition": lambda i: i.confidence < 0.85,
                "reason": "Low confidence action"
            },
        ]
    
    def _build_block_rules(self) -> List[dict]:
        """
        Absolutely blocked actions (FORBIDDEN or CRITICAL risk)
        OpenAssistant risk levels 8-9
        """
        return [
            # System-level threats
            {
                "pattern": "delete all",
                "reason": "Bulk deletion forbidden",
                "risk": RiskLevel.FORBIDDEN.value
            },
            {
                "pattern": "format drive",
                "reason": "Drive formatting forbidden",
                "risk": RiskLevel.FORBIDDEN.value
            },
            {
                "pattern": "system shutdown",
                "reason": "System shutdown forbidden",
                "risk": RiskLevel.CRITICAL.value
            },
            {
                "pattern": "remove user",
                "reason": "User deletion forbidden",
                "risk": RiskLevel.CRITICAL.value
            },
            
            # Multi-confirmation for compound actions
            {
                "compound": ["delete", "all"],
                "reason": "Compound destructive action forbidden",
                "risk": RiskLevel.FORBIDDEN.value
            },
        ]
    
    def _build_acl_rules(self) -> List[dict]:
        """
        Access Control List following Home Assistant pattern
        Domain-based permission system
        """
        return [
            # File system permissions
            {
                "domain": "filesystem",
                "actions": ["read", "write"],
                "paths": ["documents", "downloads"],
                "allow": True
            },
            {
                "domain": "filesystem",
                "actions": ["delete", "format"],
                "paths": ["system32", "windows"],
                "allow": False
            },
            
            # Application permissions
            {
                "domain": "application",
                "actions": ["open", "close"],
                "apps": ["chrome", "notepad", "calculator"],
                "allow": True
            },
            {
                "domain": "application",
                "actions": ["uninstall"],
                "allow": False
            },
            
            # System permissions
            {
                "domain": "system",
                "actions": ["shutdown", "restart"],
                "allow": False
            },
        ]
    
    def _check_confirmation_rules(self, intent: Intent) -> bool:
        """Check if intent requires confirmation"""
        for rule in self.confirmation_rules:
            # Exact action match
            if rule.get("action") == intent.action:
                if rule.get("always"):
                    return True
                # Conditional
                if "condition" in rule:
                    if rule["condition"](intent):
                        return True
        
        # Risk-based confirmation (OpenAssistant taxonomy)
        if intent.risk_level >= int(RiskLevel.HIGH.value):
            return True
        
        return False
    
    def _check_block_rules(self, intent: Intent) -> Optional[str]:
        """Check if intent should be blocked with reason"""
        text = intent.text.lower()
        
        for rule in self.block_rules:
            # Pattern matching
            if "pattern" in rule:
                if rule["pattern"] in text:
                    return rule["reason"]
            
            # Compound pattern (multiple keywords)
            if "compound" in rule:
                if all(keyword in text for keyword in rule["compound"]):
                    return rule["reason"]
        
        # Risk level check
        if intent.risk_level >= int(RiskLevel.FORBIDDEN.value):
            return f"Action blocked: Risk level {intent.risk_level}"
        
        return None
    
    def _check_acl_rules(self, intent: Intent) -> bool:
        """Validate Access Control List"""
        # Simplified ACL: if no explicit deny, allow
        for rule in self.acl_rules:
            domain = rule.get("domain")
            
            # Filesystem access
            if domain == "filesystem" and intent.target:
                if not rule.get("allow"):
                    if any(blocked in intent.target for blocked in rule.get("paths", [])):
                        return False
            
            # System operations
            if domain == "system" and intent.action in rule.get("actions", []):
                if not rule.get("allow"):
                    return False
        
        return True
    
    def _get_risk_description(self, intent: Intent) -> str:
        """Get human-readable risk description"""
        risk_descriptions = {
            0: "No risk - safe operation",
            2: "Low risk - standard operation",
            4: "Medium risk - requires context",
            6: "High risk - requires confirmation",
            8: "Critical risk - usually blocked",
            9: "Forbidden - always blocked",
        }
        return risk_descriptions.get(intent.risk_level, "Unknown risk")
