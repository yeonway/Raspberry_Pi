from app.services.validators.base import (
    VALIDATION_FAILED,
    VALIDATION_MANUAL_REVIEW_REQUIRED,
    ValidationContext,
    ValidationTimer,
    result,
)


class RubricValidator:
    method = "rubric"

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        if not context.rubric:
            return result(self.method, VALIDATION_FAILED, timer, message="Rubric is required for manual review.")
        return result(
            self.method,
            VALIDATION_MANUAL_REVIEW_REQUIRED,
            timer,
            message="Automatic validation is not supported for this format.",
        )
