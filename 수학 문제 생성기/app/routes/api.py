import json
from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import (
    GenerationLog,
    Problem,
    ProblemFormat,
    ProblemSet,
    RenderedAsset,
    Subject,
    Textbook,
    Unit,
    UnitAllowedFormat,
    ValidationResult,
)
from app.services.ai.base import (
    AIProviderError,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.schemas import SIMPLE_AI_TEST_SCHEMA
from app.services.generation_planner import GenerateRequest, GenerationPlanner
from app.services.generation_service import GenerationService, GenerationServiceError
from app.services.problem_formats import get_allowed_format_options
from app.services.problem_sets import delete_problem_set
from app.services.rendering_service import RenderingService
from app.services.validation_service import ValidationService


router = APIRouter()


class AITestRequest(BaseModel):
    prompt: str = Field(
        default='Return JSON only: {"ok": true, "message": "gemini provider test"}',
        max_length=1000,
    )
    model_name: str | None = Field(default=None, max_length=120)
    temperature: float = Field(default=0.1, ge=0, le=2)


class GenerationPlanRequest(BaseModel):
    subject_id: int
    textbook_id: int | None = None
    unit_id: int
    difficulty_level: int = Field(default=3, ge=1, le=5)
    requested_count: int = Field(default=5, ge=1, le=10)
    generation_mode: Literal["selected", "random", "mixed_random", "instruction_guided"]
    selected_format_codes: list[str] = Field(default_factory=list)
    format_weights: dict[str, float] = Field(default_factory=dict)
    generation_instruction: str = Field(default="", max_length=2000)
    random_seed: int | None = None
    explanation_style: Literal["short", "normal", "detailed"] = "normal"
    include_answers: bool = True
    title: str | None = Field(default=None, max_length=200)


class GenerateProblemsRequest(GenerationPlanRequest):
    pass


@router.get("/health")
def api_health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/ai/status")
def ai_status() -> dict:
    provider = build_ai_provider()
    return provider.status()


@router.post("/ai/test")
def ai_test(payload: AITestRequest, session: Session = Depends(get_session)) -> dict:
    provider = build_ai_provider()
    model_name = payload.model_name or provider.default_model
    log = GenerationLog(
        provider=provider.provider_name,
        model_name=model_name,
        request_summary=_truncate(payload.prompt),
        status="pending",
    )
    session.add(log)
    session.commit()

    try:
        result = provider.generate_structured(
            prompt=payload.prompt,
            schema=SIMPLE_AI_TEST_SCHEMA,
            model_name=model_name,
            temperature=payload.temperature,
        )
    except ProviderConfigurationError as exc:
        _finish_generation_log(session, log, "configuration_error", error_message=str(exc))
        raise HTTPException(status_code=503, detail={"available": False, "error": str(exc)}) from exc
    except ProviderRateLimitError as exc:
        _finish_generation_log(session, log, "rate_limited", error_message=str(exc))
        raise HTTPException(status_code=503, detail={"available": False, "error": str(exc)}) from exc
    except ProviderNetworkError as exc:
        _finish_generation_log(session, log, "network_error", error_message=str(exc))
        raise HTTPException(status_code=502, detail={"available": False, "error": str(exc)}) from exc
    except ProviderResponseError as exc:
        _finish_generation_log(session, log, "response_error", error_message=str(exc))
        raise HTTPException(status_code=502, detail={"available": False, "error": str(exc)}) from exc
    except AIProviderError as exc:
        _finish_generation_log(session, log, "provider_error", error_message=str(exc))
        raise HTTPException(status_code=502, detail={"available": False, "error": "AI provider failed."}) from exc

    _finish_generation_log(session, log, "success", response_summary=_truncate(result.raw_text))
    return {
        "available": True,
        "provider": result.provider,
        "model_name": result.model_name,
        "key_id": result.key_id,
        "data": result.data,
    }


@router.post("/generation/plan")
def create_generation_plan(payload: GenerationPlanRequest, session: Session = Depends(get_session)) -> dict:
    unit = session.get(Unit, payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")

    allowed_formats = get_allowed_format_options(session, payload.unit_id)
    request = GenerateRequest(
        subject_id=payload.subject_id,
        textbook_id=payload.textbook_id,
        unit_id=payload.unit_id,
        difficulty_level=payload.difficulty_level,
        requested_count=payload.requested_count,
        generation_mode=payload.generation_mode,
        selected_format_codes=payload.selected_format_codes,
        format_weights=payload.format_weights,
        generation_instruction=payload.generation_instruction,
        random_seed=payload.random_seed,
        explanation_style=payload.explanation_style,
        include_answers=payload.include_answers,
    )
    plan = GenerationPlanner().build_plan(request, allowed_formats)
    return asdict(plan)


@router.post("/generate")
def generate_problems(payload: GenerateProblemsRequest, session: Session = Depends(get_session)) -> dict:
    request = _to_generate_request(payload)
    try:
        problem_set = GenerationService(build_ai_provider()).generate(session, request)
    except GenerationServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_problem_set(session, problem_set.id, include_problems=True)


@router.post("/generation/create")
def create_generated_problem_set(payload: GenerateProblemsRequest, session: Session = Depends(get_session)) -> dict:
    provider = build_ai_provider()
    if not provider.status()["available"]:
        raise HTTPException(
            status_code=503,
            detail={"available": False, "error": "Gemini API key is not configured."},
        )

    request = _to_generate_request(payload)
    try:
        problem_set = GenerationService(provider).generate(session, request)
    except GenerationServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    data = serialize_problem_set(session, problem_set.id, include_problems=True)
    problems = data.get("problems", [])
    errors = [
        problem.get("validation_message") or "Problem generation failed."
        for problem in problems
        if problem.get("validation_status") == "generation_failed"
    ]
    return {
        "problem_set_id": problem_set.id,
        "status": problem_set.status,
        "requested_count": problem_set.requested_count,
        "generated_count": sum(1 for problem in problems if problem.get("validation_status") != "generation_failed"),
        "problems": problems,
        "warnings": [],
        "errors": errors,
    }


@router.get("/problem-sets")
def list_problem_sets(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    unit_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[dict]:
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    query = select(ProblemSet)
    if status:
        query = query.where(ProblemSet.status == status)
    if unit_id is not None:
        query = query.where(ProblemSet.unit_id == unit_id)
    problem_sets = session.scalars(
        query.order_by(ProblemSet.created_at.desc()).offset(safe_offset).limit(safe_limit)
    ).all()
    return [serialize_problem_set(session, problem_set.id, include_problems=False) for problem_set in problem_sets]


@router.get("/problems")
def list_problems(
    limit: int = 20,
    offset: int = 0,
    problem_set_id: int | None = None,
    validation_status: str | None = None,
    format_code: str | None = None,
    session: Session = Depends(get_session),
) -> list[dict]:
    safe_limit = min(max(limit, 1), 100)
    safe_offset = max(offset, 0)
    query = select(Problem)
    if problem_set_id is not None:
        query = query.where(Problem.problem_set_id == problem_set_id)
    if validation_status:
        query = query.where(Problem.validation_status == validation_status)
    if format_code:
        query = query.where(Problem.format_code == format_code)
    problems = session.scalars(query.order_by(Problem.created_at.desc(), Problem.id.desc()).offset(safe_offset).limit(safe_limit)).all()
    return [serialize_problem(problem) for problem in problems]


@router.get("/problem-sets/{problem_set_id}")
def get_problem_set(problem_set_id: int, session: Session = Depends(get_session)) -> dict:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    return serialize_problem_set(session, problem_set_id, include_problems=True)


@router.delete("/problem-sets/{problem_set_id}")
def delete_problem_set_endpoint(problem_set_id: int, session: Session = Depends(get_session)) -> dict:
    result = delete_problem_set(session, problem_set_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    return {
        "deleted": True,
        "problem_set_id": result.problem_set_id,
        "deleted_problem_count": result.deleted_problem_count,
    }


@router.get("/problem-sets/{problem_set_id}/logs")
def list_problem_set_logs(problem_set_id: int, session: Session = Depends(get_session)) -> list[dict]:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    logs = session.scalars(
        select(GenerationLog).where(GenerationLog.problem_set_id == problem_set_id).order_by(GenerationLog.id)
    ).all()
    return [serialize_generation_log(log) for log in logs]


@router.get("/problems/{problem_id}")
def get_problem(problem_id: int, session: Session = Depends(get_session)) -> dict:
    problem = session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    return serialize_problem(problem)


@router.post("/validate/problem/{problem_id}")
def validate_problem(problem_id: int, session: Session = Depends(get_session)) -> dict:
    problem = session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    validation_result = ValidationService().validate_problem(session, problem)
    return serialize_validation_result(validation_result)


@router.post("/validate/problem-set/{problem_set_id}")
def validate_problem_set(problem_set_id: int, session: Session = Depends(get_session)) -> dict:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    results = ValidationService().validate_problem_set(session, problem_set_id)
    return {
        "problem_set_id": problem_set_id,
        "validated_count": len(results),
        "results": [serialize_validation_result(result) for result in results],
    }


@router.post("/problems/{problem_id}/render")
def render_problem(problem_id: int, session: Session = Depends(get_session)) -> dict:
    problem = session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    asset = RenderingService().render_problem(session, problem)
    return serialize_rendered_asset(asset)


@router.post("/problem-sets/{problem_set_id}/render")
def render_problem_set(problem_set_id: int, session: Session = Depends(get_session)) -> dict:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    assets = RenderingService().render_problem_set(session, problem_set_id)
    return {
        "problem_set_id": problem_set_id,
        "rendered_count": len(assets),
        "assets": [serialize_rendered_asset(asset) for asset in assets],
    }


@router.get("/subjects")
def list_subjects(session: Session = Depends(get_session)) -> list[dict]:
    subjects = session.scalars(select(Subject).order_by(Subject.id)).all()
    return [
        {
            "id": subject.id,
            "code": subject.code,
            "name": subject.name,
            "description": subject.description,
            "is_active": subject.is_active,
            "created_at": subject.created_at.isoformat(),
        }
        for subject in subjects
    ]


@router.get("/textbooks")
def list_textbooks(
    subject_id: int | None = None,
    grade_label: str | None = None,
    session: Session = Depends(get_session),
) -> list[dict]:
    query = select(Textbook)
    if subject_id is not None:
        query = query.where(Textbook.subject_id == subject_id)
    if grade_label:
        query = query.where(Textbook.grade_label == grade_label)
    textbooks = session.scalars(query.order_by(Textbook.grade_label, Textbook.id)).all()
    return [
        {
            "id": textbook.id,
            "subject_id": textbook.subject_id,
            "publisher": textbook.publisher,
            "title": textbook.title,
            "grade_label": textbook.grade_label,
            "curriculum_version": textbook.curriculum_version,
            "metadata_json": textbook.metadata_json,
            "is_active": textbook.is_active,
            "created_at": textbook.created_at.isoformat(),
        }
        for textbook in textbooks
    ]


@router.get("/units")
def list_units(
    subject_id: int | None = None,
    grade_label: str | None = None,
    semester_label: str | None = None,
    session: Session = Depends(get_session),
) -> list[dict]:
    query = select(Unit)
    if subject_id is not None:
        query = query.where(Unit.subject_id == subject_id)
    if grade_label:
        query = query.where(Unit.grade_label == grade_label)
    units = session.scalars(query.order_by(Unit.grade_label, Unit.sort_order, Unit.id)).all()
    if semester_label:
        units = [unit for unit in units if _unit_metadata(unit).get("semester_label") == semester_label]
    return [
        {
            "id": unit.id,
            "subject_id": unit.subject_id,
            "textbook_id": unit.textbook_id,
            "parent_id": unit.parent_id,
            "grade_label": unit.grade_label,
            "name": unit.name,
            "description": unit.description,
            "learning_goal": unit.learning_goal,
            "semester_label": _unit_metadata(unit).get("semester_label", ""),
            "area": _unit_metadata(unit).get("area", ""),
            "sort_order": unit.sort_order,
            "metadata_json": unit.metadata_json,
            "is_active": unit.is_active,
            "created_at": unit.created_at.isoformat(),
        }
        for unit in units
    ]


@router.get("/problem-formats")
def list_problem_formats(session: Session = Depends(get_session)) -> list[dict]:
    formats = session.scalars(select(ProblemFormat).order_by(ProblemFormat.id)).all()
    return [
        {
            "id": problem_format.id,
            "code": problem_format.code,
            "name": problem_format.name,
            "description": problem_format.description,
            "requires_choices": problem_format.requires_choices,
            "requires_rubric": problem_format.requires_rubric,
            "supports_auto_validation": problem_format.supports_auto_validation,
            "supports_rendering": problem_format.supports_rendering,
            "default_validation_method": problem_format.default_validation_method,
            "default_rendering_type": problem_format.default_rendering_type,
            "is_active": problem_format.is_active,
        }
        for problem_format in formats
    ]


@router.get("/units/{unit_id}/allowed-formats")
def list_unit_allowed_formats(unit_id: int, session: Session = Depends(get_session)) -> list[dict]:
    unit = session.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")

    rows = session.execute(
        select(UnitAllowedFormat, ProblemFormat)
        .join(ProblemFormat, UnitAllowedFormat.problem_format_id == ProblemFormat.id)
        .where(UnitAllowedFormat.unit_id == unit_id)
        .order_by(ProblemFormat.id)
    ).all()
    return [
        {
            "id": allowed.id,
            "unit_id": allowed.unit_id,
            "problem_format_id": problem_format.id,
            "code": problem_format.code,
            "name": problem_format.name,
            "default_weight": allowed.default_weight,
            "min_difficulty": allowed.min_difficulty,
            "max_difficulty": allowed.max_difficulty,
            "is_active": allowed.is_active,
        }
        for allowed, problem_format in rows
    ]


def _finish_generation_log(
    session: Session,
    log: GenerationLog,
    status: str,
    response_summary: str = "",
    error_message: str | None = None,
) -> None:
    log.status = status
    log.response_summary = response_summary
    log.error_message = _truncate(error_message) if error_message else None
    session.add(log)
    session.commit()


def _truncate(value: str | None, limit: int = 500) -> str:
    if value is None:
        return ""
    return value[:limit]


def build_ai_provider() -> GeminiProvider:
    return GeminiProvider()


def _to_generate_request(payload: GenerationPlanRequest) -> GenerateRequest:
    return GenerateRequest(
        subject_id=payload.subject_id,
        textbook_id=payload.textbook_id,
        unit_id=payload.unit_id,
        difficulty_level=payload.difficulty_level,
        requested_count=payload.requested_count,
        generation_mode=payload.generation_mode,
        selected_format_codes=payload.selected_format_codes,
        format_weights=payload.format_weights,
        generation_instruction=payload.generation_instruction,
        random_seed=payload.random_seed,
        explanation_style=payload.explanation_style,
        include_answers=payload.include_answers,
        title=payload.title,
    )


def serialize_problem_set(session: Session, problem_set_id: int, include_problems: bool = False) -> dict:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    data = {
        "id": problem_set.id,
        "title": problem_set.title,
        "subject_id": problem_set.subject_id,
        "textbook_id": problem_set.textbook_id,
        "unit_id": problem_set.unit_id,
        "difficulty_level": problem_set.difficulty_level,
        "generation_mode": problem_set.generation_mode,
        "generation_instruction": problem_set.generation_instruction,
        "requested_count": problem_set.requested_count,
        "status": problem_set.status,
        "created_at": problem_set.created_at.isoformat(),
    }
    if include_problems:
        problems = session.scalars(
            select(Problem).where(Problem.problem_set_id == problem_set.id).order_by(Problem.id)
        ).all()
        assets = RenderingService().latest_assets_by_problem(session, [problem.id for problem in problems])
        data["problems"] = [serialize_problem(problem, assets.get(problem.id)) for problem in problems]
    return data


def serialize_problem(problem: Problem, rendered_asset: RenderedAsset | None = None) -> dict:
    data = {
        "id": problem.id,
        "problem_set_id": problem.problem_set_id,
        "subject_id": problem.subject_id,
        "textbook_id": problem.textbook_id,
        "unit_id": problem.unit_id,
        "format_code": problem.format_code,
        "difficulty_level": problem.difficulty_level,
        "question_text": problem.question_text,
        "answer_text": problem.answer_text,
        "explanation_text": problem.explanation_text,
        "input_schema_json": problem.input_schema_json,
        "answer_schema_json": problem.answer_schema_json,
        "choices_json": problem.choices_json,
        "rubric_json": problem.rubric_json,
        "rendering_type": problem.rendering_type,
        "rendering_payload_json": problem.rendering_payload_json,
        "validation_method": problem.validation_method,
        "validation_status": problem.validation_status,
        "validation_message": problem.validation_message,
        "created_at": problem.created_at.isoformat(),
    }
    if rendered_asset is not None:
        data["rendered_asset"] = serialize_rendered_asset(rendered_asset)
    return data


def serialize_validation_result(validation_result: ValidationResult) -> dict:
    return {
        "id": validation_result.id,
        "problem_id": validation_result.problem_id,
        "method": validation_result.method,
        "status": validation_result.status,
        "expected_answer": validation_result.expected_answer,
        "computed_answer": validation_result.computed_answer,
        "message": validation_result.message,
        "duration_ms": validation_result.duration_ms,
        "created_at": validation_result.created_at.isoformat(),
    }


def serialize_rendered_asset(asset: RenderedAsset) -> dict:
    return {
        "id": asset.id,
        "problem_id": asset.problem_id,
        "rendering_type": asset.rendering_type,
        "payload_hash": asset.payload_hash,
        "file_path": asset.file_path,
        "asset_url": f"/rendered/{asset.file_path}" if asset.file_path else None,
        "content_html": asset.content_html,
        "status": asset.status,
        "message": asset.message,
        "created_at": asset.created_at.isoformat(),
    }


def serialize_generation_log(log: GenerationLog) -> dict:
    return {
        "id": log.id,
        "problem_set_id": log.problem_set_id,
        "provider": log.provider,
        "model_name": log.model_name,
        "request_summary": log.request_summary,
        "response_summary": log.response_summary,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat(),
    }


def _unit_metadata(unit: Unit) -> dict:
    try:
        data = json.loads(unit.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
