from app.services.validators.base import (
    VALIDATION_AUTO_VALIDATED,
    VALIDATION_FAILED,
    VALIDATION_UNSUPPORTED,
    ValidationContext,
    ValidationTimer,
    result,
)


class TableInterpretationValidator:
    method = "table_interpretation"

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        payload = context.rendering_payload or {}
        table = payload.get("table") or payload.get("rows")
        expected = context.answer_schema.get("value", context.answer_text)
        candidate = context.answer_schema.get("auto_validation_candidate", {}).get("value", context.answer_text)
        if not table:
            return result(self.method, VALIDATION_FAILED, timer, message="Table data is required.")
        if expected is None or candidate is None:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="No comparable table answer was provided.")
        status = VALIDATION_AUTO_VALIDATED if str(expected).strip() == str(candidate).strip() else VALIDATION_FAILED
        return result(self.method, status, timer, str(expected), str(candidate))
