from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Problem, ValidationResult
from app.services.validators.base import ValidationContext, safe_json_loads
from app.services.validators.registry import ValidatorRegistry


class ValidationService:
    def __init__(self, registry: ValidatorRegistry | None = None):
        self.registry = registry or ValidatorRegistry()
        self.settings = get_settings()

    def validate_problem(self, session: Session, problem: Problem) -> ValidationResult:
        context = self._context_from_problem(problem)
        result = self.registry.validate(context)

        validation_result = ValidationResult(
            problem_id=problem.id,
            method=result.method,
            status=result.status,
            expected_answer=result.expected_answer,
            computed_answer=result.computed_answer,
            message=result.message,
            duration_ms=result.duration_ms,
        )
        problem.validation_status = result.status
        problem.validation_message = result.message
        session.add(validation_result)
        session.add(problem)
        session.commit()
        session.refresh(validation_result)
        return validation_result

    def validate_problem_set(self, session: Session, problem_set_id: int) -> list[ValidationResult]:
        problems = session.scalars(
            select(Problem).where(Problem.problem_set_id == problem_set_id).order_by(Problem.id)
        ).all()
        return [self.validate_problem(session, problem) for problem in problems]

    def _context_from_problem(self, problem: Problem) -> ValidationContext:
        answer_schema = safe_json_loads(problem.answer_schema_json, {})
        choices = safe_json_loads(problem.choices_json, None)
        rubric = safe_json_loads(problem.rubric_json, None)
        rendering_payload = safe_json_loads(problem.rendering_payload_json, None)
        return ValidationContext(
            format_code=problem.format_code,
            validation_method=problem.validation_method,
            question_text=problem.question_text,
            answer_text=problem.answer_text,
            input_schema=safe_json_loads(problem.input_schema_json, {}),
            answer_schema=answer_schema if isinstance(answer_schema, dict) else {},
            choices=choices if isinstance(choices, list) else None,
            rubric=rubric if isinstance(rubric, dict) else None,
            rendering_type=problem.rendering_type,
            rendering_payload=rendering_payload if isinstance(rendering_payload, dict) else None,
            timeout_seconds=self.settings.validation_timeout_seconds,
        )
