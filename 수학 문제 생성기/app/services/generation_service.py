import json
from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import GenerationLog, Problem, ProblemSet, Subject, Textbook, Unit
from app.services.ai.base import AIProvider, AIProviderError, ProviderResponseError
from app.services.ai.problem_prompts import build_problem_prompt
from app.services.ai.problem_schemas import PROBLEM_JSON_SCHEMA
from app.services.generation_planner import GenerateRequest, GenerationPlanner, ProblemGenerationPlan, ProblemSlot
from app.services.problem_formats import get_allowed_format_options


class GenerationServiceError(Exception):
    """Raised when a generation request cannot be planned or saved."""


class GenerationService:
    def __init__(self, provider: AIProvider):
        self.provider = provider
        self.settings = get_settings()

    def generate(self, session: Session, request: GenerateRequest) -> ProblemSet:
        if request.requested_count > self.settings.max_problems_per_generation:
            raise GenerationServiceError(
                f"requested_count exceeds max_problems_per_generation={self.settings.max_problems_per_generation}"
            )

        subject = session.get(Subject, request.subject_id)
        unit = session.get(Unit, request.unit_id)
        textbook = session.get(Textbook, request.textbook_id) if request.textbook_id else None
        if subject is None:
            raise GenerationServiceError("Subject not found.")
        if unit is None:
            raise GenerationServiceError("Unit not found.")

        plan = self._build_plan(session, request)
        if not plan.problem_slots:
            message = "Generation plan has no problem slots."
            if plan.warnings:
                message = f"{message} {' '.join(plan.warnings)}"
            raise GenerationServiceError(message)

        problem_set = ProblemSet(
            title=request.title or f"{unit.grade_label} {unit.name} 문제 세트",
            subject_id=request.subject_id,
            textbook_id=request.textbook_id,
            unit_id=request.unit_id,
            difficulty_level=request.difficulty_level,
            generation_mode=request.generation_mode,
            generation_instruction=request.generation_instruction,
            requested_count=request.requested_count,
            status="planned",
        )
        session.add(problem_set)
        session.commit()
        session.refresh(problem_set)

        problem_set.status = "generating"
        session.add(problem_set)
        session.commit()

        success_count = 0
        failure_count = 0
        for slot in plan.problem_slots:
            prompt = build_problem_prompt(
                subject=subject,
                textbook=textbook,
                unit=unit,
                slot=slot,
                generation_instruction=request.generation_instruction,
                explanation_style=request.explanation_style,
                include_answers=request.include_answers,
            )
            log = self._create_log(session, problem_set.id, prompt)

            try:
                result = self.provider.generate_structured(
                    prompt=prompt,
                    schema=PROBLEM_JSON_SCHEMA,
                    model_name=None,
                    temperature=0.3,
                )
            except ProviderResponseError as exc:
                failure_count += 1
                self._mark_log_failed(session, log, "response_error", str(exc))
                self._save_failed_problem(session, problem_set.id, request, slot, str(exc))
                continue
            except AIProviderError as exc:
                failure_count += 1
                self._mark_log_failed(session, log, "provider_error", str(exc))
                self._save_failed_problem(session, problem_set.id, request, slot, str(exc))
                continue

            validation_status = _initial_validation_status(result.data, slot)
            self._save_problem(session, problem_set.id, request, slot, result.data, validation_status)
            log.status = "success"
            log.model_name = result.model_name
            log.response_summary = _truncate(result.raw_text)
            session.add(log)
            session.commit()
            success_count += 1

        if success_count == len(plan.problem_slots) and failure_count == 0:
            problem_set.status = "generated"
        elif success_count > 0:
            problem_set.status = "partially_failed"
        else:
            problem_set.status = "failed"
        session.add(problem_set)
        session.commit()
        session.refresh(problem_set)
        return problem_set

    def _build_plan(self, session: Session, request: GenerateRequest) -> ProblemGenerationPlan:
        allowed_formats = get_allowed_format_options(session, request.unit_id)
        return GenerationPlanner().build_plan(request, allowed_formats)

    def _create_log(self, session: Session, problem_set_id: int, prompt: str) -> GenerationLog:
        provider_name = getattr(self.provider, "provider_name", "unknown")
        default_model = getattr(self.provider, "default_model", "")
        log = GenerationLog(
            problem_set_id=problem_set_id,
            provider=provider_name,
            model_name=default_model,
            request_summary=_truncate(prompt),
            status="pending",
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log

    def _mark_log_failed(self, session: Session, log: GenerationLog, status: str, error_message: str) -> None:
        log.status = status
        log.error_message = _truncate(error_message)
        session.add(log)
        session.commit()

    def _save_failed_problem(
        self,
        session: Session,
        problem_set_id: int,
        request: GenerateRequest,
        slot: ProblemSlot,
        message: str,
    ) -> None:
        problem = Problem(
            problem_set_id=problem_set_id,
            subject_id=request.subject_id,
            textbook_id=request.textbook_id,
            unit_id=request.unit_id,
            format_code=slot.format_code,
            difficulty_level=slot.difficulty_level,
            question_text="문제 생성 실패",
            answer_text="",
            explanation_text="",
            input_schema_json="{}",
            answer_schema_json="{}",
            choices_json=None,
            rubric_json=None,
            rendering_type=slot.rendering_type,
            rendering_payload_json=None,
            validation_method=slot.validation_method,
            validation_status="generation_failed",
            validation_message=_truncate(message),
        )
        session.add(problem)
        session.commit()

    def _save_problem(
        self,
        session: Session,
        problem_set_id: int,
        request: GenerateRequest,
        slot: ProblemSlot,
        data: dict[str, Any],
        validation_status: str,
    ) -> None:
        answer_schema = data.get("answer_schema") or {}
        if "auto_validation_candidate" in data:
            answer_schema = {**answer_schema, "auto_validation_candidate": data.get("auto_validation_candidate")}
        if "correct_index" in data:
            answer_schema = {**answer_schema, "correct_index": data.get("correct_index")}

        problem = Problem(
            problem_set_id=problem_set_id,
            subject_id=request.subject_id,
            textbook_id=request.textbook_id,
            unit_id=request.unit_id,
            format_code=str(data.get("format_code") or slot.format_code),
            difficulty_level=int(data.get("difficulty_level") or slot.difficulty_level),
            question_text=str(data.get("question_text") or ""),
            answer_text=str(data.get("answer_text") or ""),
            explanation_text=str(data.get("explanation_text") or ""),
            input_schema_json=_json_dumps(data.get("input_schema") or {}),
            answer_schema_json=_json_dumps(answer_schema),
            choices_json=_json_dumps(data.get("choices")) if data.get("choices") is not None else None,
            rubric_json=_json_dumps(data.get("rubric")) if data.get("rubric") is not None else None,
            rendering_type=str(data.get("rendering_type") or slot.rendering_type),
            rendering_payload_json=(
                _json_dumps(data.get("rendering_payload")) if data.get("rendering_payload") is not None else None
            ),
            validation_method=str(data.get("validation_method") or slot.validation_method),
            validation_status=validation_status,
            validation_message=_validation_message(data, slot),
        )
        session.add(problem)
        session.commit()


def _initial_validation_status(data: dict[str, Any], slot: ProblemSlot) -> str:
    validation_method = str(data.get("validation_method") or slot.validation_method)
    if validation_method in {"manual_review", "rubric"}:
        return "manual_review_required"
    if slot.format_code == "multiple_choice" and not _valid_multiple_choice(data):
        return "needs_review"
    if slot.format_code == "graph" and not data.get("rendering_payload"):
        return "needs_review"
    if slot.format_code == "table_interpretation" and not data.get("rendering_payload"):
        return "needs_review"
    return "pending_validation"


def _valid_multiple_choice(data: dict[str, Any]) -> bool:
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) not in {4, 5}:
        return False
    if len(set(str(choice) for choice in choices)) != len(choices):
        return False
    return bool(data.get("answer_text")) or isinstance(data.get("correct_index"), int)


def _validation_message(data: dict[str, Any], slot: ProblemSlot) -> str:
    if slot.format_code == "multiple_choice" and not _valid_multiple_choice(data):
        return "multiple_choice output needs review."
    return ""


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _truncate(value: str, limit: int = 500) -> str:
    return value[:limit]
