from app.services.validators.arithmetic import ArithmeticValidator
from app.services.validators.base import (
    VALIDATION_ERROR,
    VALIDATION_MANUAL_REVIEW_REQUIRED,
    VALIDATION_UNSUPPORTED,
    ValidationContext,
    ValidationResultData,
    ValidationTimer,
    result,
)
from app.services.validators.function_value import FunctionValueValidator
from app.services.validators.graph import GraphValidator
from app.services.validators.linear_equation import LinearEquationValidator
from app.services.validators.multiple_choice import MultipleChoiceValidator
from app.services.validators.rubric import RubricValidator
from app.services.validators.system_equation import SystemEquationValidator
from app.services.validators.table import TableInterpretationValidator


class ValidatorRegistry:
    def __init__(self):
        self._validators = {
            "arithmetic": ArithmeticValidator(),
            "linear_equation": LinearEquationValidator(),
            "system_equation": SystemEquationValidator(),
            "function_value": FunctionValueValidator(),
            "multiple_choice": MultipleChoiceValidator(),
            "graph": GraphValidator(),
            "table_interpretation": TableInterpretationValidator(),
            "rubric": RubricValidator(),
            "manual_review": RubricValidator(),
        }

    def validate(self, context: ValidationContext) -> ValidationResultData:
        method = self._choose_method(context)
        validator = self._validators.get(method)
        if validator is None:
            timer = ValidationTimer(context.timeout_seconds)
            return result(method, VALIDATION_UNSUPPORTED, timer, message=f"No validator registered for {method}.")
        try:
            return validator.validate(context)
        except Exception as exc:
            timer = ValidationTimer(context.timeout_seconds)
            return result(method, VALIDATION_ERROR, timer, message=str(exc))

    def _choose_method(self, context: ValidationContext) -> str:
        if context.format_code in {"descriptive", "proof", "solution_steps"}:
            return "rubric"
        if context.validation_method in self._validators:
            return context.validation_method
        if context.format_code in self._validators:
            return context.format_code
        if context.format_code == "short_answer":
            schema_type = str(context.input_schema.get("type") or context.answer_schema.get("type") or "")
            if schema_type in self._validators:
                return schema_type
            return "arithmetic"
        if context.validation_method in {"manual", "manual_review"}:
            return "manual_review"
        return context.validation_method or VALIDATION_MANUAL_REVIEW_REQUIRED
