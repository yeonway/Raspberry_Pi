import sympy as sp

from app.services.validators.base import (
    VALIDATION_AUTO_VALIDATED,
    VALIDATION_ERROR,
    VALIDATION_FAILED,
    VALIDATION_UNSUPPORTED,
    ValidationContext,
    ValidationTimer,
    result,
)


class FunctionValueValidator:
    method = "function_value"

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        equation = str(context.input_schema.get("equation") or "")
        x_value = context.input_schema.get("x")
        expected = context.answer_schema.get("y", context.answer_text)
        if not equation or x_value is None:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Equation and x value are required.")
        if len(equation) > 80 or "^" in equation:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Only simple y = ax + b forms are supported.")

        try:
            x = sp.Symbol("x")
            text = equation.split("=", 1)[-1]
            expr = sp.sympify(text)
            if expr.free_symbols - {x}:
                return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Only x variable is supported.")
            if sp.Poly(expr, x).degree() > 1:
                return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Only linear functions are supported.")
            computed = sp.simplify(expr.subs(x, sp.sympify(x_value)))
            expected_value = sp.sympify(expected)
            status = VALIDATION_AUTO_VALIDATED if sp.simplify(computed - expected_value) == 0 else VALIDATION_FAILED
            return result(self.method, status, timer, str(expected_value), str(computed))
        except Exception as exc:
            return result(self.method, VALIDATION_ERROR, timer, str(expected), message=str(exc))
