import re

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


class LinearEquationValidator:
    method = "linear_equation"
    max_equation_length = 120

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        equation = str(context.input_schema.get("equation") or "").strip()
        variable_name = str(context.answer_schema.get("variable") or context.input_schema.get("variable") or "x")
        expected = str(context.answer_text or context.answer_schema.get("value") or "").strip()
        if not equation or "=" not in equation:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="No linear equation provided.")
        if len(equation) > self.max_equation_length:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Equation is too long.")
        if not re.fullmatch(r"[0-9a-zA-Z_+\-*/().= ]+", equation):
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Equation contains unsupported characters.")

        try:
            variable = sp.Symbol(variable_name)
            left_text, right_text = equation.split("=", 1)
            left = sp.sympify(left_text)
            right = sp.sympify(right_text)
            symbols = (left - right).free_symbols
            if symbols - {variable} or len(symbols) > 1:
                return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Only one variable is supported.")
            if sp.Poly(left - right, variable).degree() > 1:
                return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Only first-degree equations are supported.")
            if timer.expired():
                return result(self.method, VALIDATION_ERROR, timer, message="Validation timed out.")
            solution = sp.solve(sp.Eq(left, right), variable)
            if len(solution) != 1:
                return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Expected exactly one solution.")
            computed = sp.simplify(solution[0])
            expected_value = _parse_expected(expected, variable_name)
            status = VALIDATION_AUTO_VALIDATED if sp.simplify(computed - expected_value) == 0 else VALIDATION_FAILED
            return result(self.method, status, timer, str(expected_value), str(computed))
        except Exception as exc:
            return result(self.method, VALIDATION_ERROR, timer, expected, message=str(exc))


def _parse_expected(expected: str, variable_name: str):
    cleaned = expected.strip()
    if "=" in cleaned:
        _, cleaned = cleaned.split("=", 1)
    cleaned = cleaned.replace(variable_name, "").strip()
    return sp.sympify(cleaned)
