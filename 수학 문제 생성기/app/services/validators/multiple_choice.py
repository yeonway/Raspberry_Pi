from app.services.validators.base import (
    VALIDATION_AUTO_VALIDATED,
    VALIDATION_FAILED,
    VALIDATION_UNSUPPORTED,
    ValidationContext,
    ValidationTimer,
    result,
)


class MultipleChoiceValidator:
    method = "multiple_choice"

    def validate(self, context: ValidationContext):
        timer = ValidationTimer(context.timeout_seconds)
        choices = context.choices
        if not isinstance(choices, list) or len(choices) not in {4, 5}:
            return result(self.method, VALIDATION_FAILED, timer, message="Choices must contain 4 or 5 items.")
        normalized = [str(choice).strip() for choice in choices]
        if len(set(normalized)) != len(normalized):
            return result(self.method, VALIDATION_FAILED, timer, message="Duplicate choices were found.")

        correct_index = context.answer_schema.get("correct_index")
        answer_text = str(context.answer_text or "").strip()
        if isinstance(correct_index, int):
            if correct_index < 0 or correct_index >= len(choices):
                return result(self.method, VALIDATION_FAILED, timer, message="correct_index is out of range.")
            expected = normalized[correct_index]
            if answer_text and answer_text not in {expected, str(correct_index), str(correct_index + 1)}:
                return result(self.method, VALIDATION_FAILED, timer, expected, answer_text, "answer_text does not match correct_index.")
            return result(self.method, VALIDATION_AUTO_VALIDATED, timer, expected, expected)

        if answer_text in normalized:
            return result(self.method, VALIDATION_AUTO_VALIDATED, timer, answer_text, answer_text)
        return result(self.method, VALIDATION_UNSUPPORTED, timer, message="No usable answer_text or correct_index.")
