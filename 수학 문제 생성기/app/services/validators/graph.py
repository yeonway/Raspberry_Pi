from app.services.validators.base import (
    VALIDATION_AUTO_VALIDATED,
    VALIDATION_FAILED,
    VALIDATION_UNSUPPORTED,
    ValidationContext,
    ValidationTimer,
    result,
)


class GraphValidator:
    method = "graph"

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        payload = context.rendering_payload or {}
        if not payload:
            return result(self.method, VALIDATION_FAILED, timer, message="Graph rendering_payload is required.")
        if "equation" not in payload and "points" not in payload:
            return result(self.method, VALIDATION_UNSUPPORTED, timer, message="Graph payload needs equation or points.")
        expected = context.answer_schema.get("equation") or context.answer_schema.get("points") or context.answer_text
        computed = payload.get("equation") or payload.get("points")
        if expected and str(expected) != str(computed):
            return result(self.method, VALIDATION_FAILED, timer, str(expected), str(computed))
        return result(self.method, VALIDATION_AUTO_VALIDATED, timer, str(expected), str(computed))
