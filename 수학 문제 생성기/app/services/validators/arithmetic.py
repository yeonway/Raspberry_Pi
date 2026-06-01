from fractions import Fraction

from app.services.validators.base import (
    VALIDATION_AUTO_VALIDATED,
    VALIDATION_ERROR,
    VALIDATION_FAILED,
    VALIDATION_UNSUPPORTED,
    ValidationContext,
    ValidationTimer,
    result,
)


class ArithmeticValidator:
    method = "arithmetic"
    max_expression_length = 80
    allowed_chars = set("0123456789+-*/(). ")

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        expression = str(context.input_schema.get("expression") or "").strip()
        expected = str(context.answer_text or context.answer_schema.get("value") or "").strip()
        if not expression:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="No arithmetic expression provided.")
        if len(expression) > self.max_expression_length:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Expression is too long.")
        if any(char not in self.allowed_chars for char in expression):
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Expression contains unsupported characters.")
        if timer.expired():
            return result(self.method, VALIDATION_ERROR, timer, message="Validation timed out.")

        try:
            computed = eval(expression, {"__builtins__": {}}, {})
            computed_fraction = Fraction(computed).limit_denominator()
            expected_fraction = Fraction(expected).limit_denominator()
        except Exception as exc:
            return result(self.method, VALIDATION_ERROR, timer, expected, message=str(exc))

        status = VALIDATION_AUTO_VALIDATED if computed_fraction == expected_fraction else VALIDATION_FAILED
        return result(self.method, status, timer, expected, str(computed_fraction))
