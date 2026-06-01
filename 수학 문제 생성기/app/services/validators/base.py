import json
import time
from dataclasses import dataclass
from typing import Any, Protocol


VALIDATION_PENDING = "pending_validation"
VALIDATION_AUTO_VALIDATED = "auto_validated"
VALIDATION_FAILED = "validation_failed"
VALIDATION_NEEDS_REVIEW = "needs_review"
VALIDATION_MANUAL_REVIEW_REQUIRED = "manual_review_required"
VALIDATION_ERROR = "validation_error"
VALIDATION_UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ValidationResultData:
    method: str
    status: str
    expected_answer: str = ""
    computed_answer: str = ""
    message: str = ""
    duration_ms: int = 0


@dataclass(frozen=True)
class ValidationContext:
    format_code: str
    validation_method: str
    question_text: str
    answer_text: str
    input_schema: dict[str, Any]
    answer_schema: dict[str, Any]
    choices: list[Any] | None
    rubric: dict[str, Any] | None
    rendering_type: str
    rendering_payload: dict[str, Any] | None
    timeout_seconds: float


class ProblemValidator(Protocol):
    method: str

    def validate(self, context: ValidationContext) -> ValidationResultData:
        ...


class ValidationTimer:
    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self.started_at = time.monotonic()

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_at) * 1000)

    def expired(self) -> bool:
        return (time.monotonic() - self.started_at) > self.timeout_seconds


def safe_json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def result(
    method: str,
    status: str,
    timer: ValidationTimer,
    expected_answer: str = "",
    computed_answer: str = "",
    message: str = "",
) -> ValidationResultData:
    return ValidationResultData(
        method=method,
        status=status,
        expected_answer=expected_answer,
        computed_answer=computed_answer,
        message=message,
        duration_ms=timer.elapsed_ms(),
    )
