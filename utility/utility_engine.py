import math
import re
from core.response_model import UnifiedResponse


class UtilityEngine:
    """
    Production-Level Utility Engine

    Supports:
    - Natural language math
    - Safe evaluation
    - Time queries
    """

    def __init__(self):

        self.allowed_names = {
            name: getattr(math, name)
            for name in dir(math)
            if not name.startswith("__")
        }

        self.allowed_names.update({
            "pi": math.pi,
            "e": math.e,
            "abs": abs,
            "round": round
        })

    # ------------------------------------------------

    def handle(self, decision: dict) -> UnifiedResponse:

        action = decision.get("action")
        target = decision.get("target")
        parameters = decision.get("parameters", {})

        if action == "CALCULATE":
            expression = parameters.get("expression")
            return self.calculate(expression)

        elif action == "GET_TIME":
            return self.get_time()

        return UnifiedResponse.error_response(
            category="utility",
            spoken_message="Unsupported utility request.",
            error_code="UTILITY_UNSUPPORTED"
        )

    # ------------------------------------------------
    # NATURAL LANGUAGE CALCULATOR
    # ------------------------------------------------

    def calculate(self, expression: str) -> UnifiedResponse:

        if not expression:
            return UnifiedResponse.error_response(
                category="utility",
                spoken_message="No expression provided.",
                error_code="NO_EXPRESSION"
            )

        try:
            expression = expression.lower()

            # Replace natural language math
            expression = expression.replace("times", "*")
            expression = expression.replace("into", "*")
            expression = expression.replace("multiplied by", "*")
            expression = expression.replace("divided by", "/")
            expression = expression.replace("plus", "+")
            expression = expression.replace("minus", "-")
            expression = expression.replace("^", "**")

            # Remove extra spaces
            expression = re.sub(r"\s+", " ", expression)

            # Security validation
            if not re.match(r'^[0-9\.\+\-\*\/\%\(\)\s,a-zA-Z_]*$', expression):
                return UnifiedResponse.error_response(
                    category="utility",
                    spoken_message="Invalid characters in expression.",
                    error_code="INVALID_EXPRESSION"
                )

            result = eval(
                expression,
                {"__builtins__": None},
                self.allowed_names
            )

            return UnifiedResponse.success_response(
                category="utility",
                spoken_message=f"The result is {result}."
            )

        except Exception:
            return UnifiedResponse.error_response(
                category="utility",
                spoken_message="I could not calculate that expression.",
                error_code="CALCULATION_ERROR"
            )

    # ------------------------------------------------
    # TIME
    # ------------------------------------------------

    def get_time(self):

        from datetime import datetime

        now = datetime.now().strftime("%I:%M %p")

        return UnifiedResponse.success_response(
            category="utility",
            spoken_message=f"The current time is {now}."
        )
