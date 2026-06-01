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


class SystemEquationValidator:
    method = "system_equation"
    max_equation_length = 100

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        equations = context.input_schema.get("equations")
        variables = context.input_schema.get("variables") or ["x", "y"]
        expected_values = context.answer_schema.get("values") or {}
        if not isinstance(equations, list) or len(equations) != 2:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Exactly two equations are supported.")
        if not isinstance(variables, list) or len(variables) != 2:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Exactly two variables are supported.")
        if any(len(str(equation)) > self.max_equation_length for equation in equations):
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Equation is too long.")

        try:
            symbols = [sp.Symbol(str(name)) for name in variables]
            parsed = []
            for equation in equations:
                text = str(equation)
                if not re.fullmatch(r"[0-9a-zA-Z_+\-*/().= ]+", text):
                    return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Unsupported equation characters.")
                left, right = text.split("=", 1)
                expr = sp.sympify(left) - sp.sympify(right)
                if sp.Poly(expr, *symbols).total_degree() > 1:
                    return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Only linear systems are supported.")
                parsed.append(sp.Eq(sp.sympify(left), sp.sympify(right)))
            if timer.expired():
                return result(self.method, VALIDATION_ERROR, timer, message="Validation timed out.")
            solution = sp.solve(parsed, symbols, dict=True)
            if len(solution) != 1:
                return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Expected exactly one solution.")
            computed = {str(symbol): sp.simplify(solution[0][symbol]) for symbol in symbols}
            expected = {str(key): sp.sympify(value) for key, value in expected_values.items()}
            ok = all(str(key) in computed and sp.simplify(computed[str(key)] - value) == 0 for key, value in expected.items())
            return result(self.method, VALIDATION_AUTO_VALIDATED if ok else VALIDATION_FAILED, timer, str(expected), str(computed))
        except Exception as exc:
            return result(self.method, VALIDATION_ERROR, timer, message=str(exc))
