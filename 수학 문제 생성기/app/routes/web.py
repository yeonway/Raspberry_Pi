import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import GenerationLog, Problem, ProblemFormat, ProblemSet, Subject, Textbook, Unit, UnitAllowedFormat
from app.services.ai.gemini_provider import GeminiProvider
from app.services.generation_planner import GenerateRequest
from app.services.generation_service import GenerationService, GenerationServiceError
from app.services.problem_sets import delete_problem_set
from app.services.rendering_service import RenderingService
from app.services.validation_service import ValidationService

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    subjects = session.scalars(select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.id)).all()
    textbooks = session.scalars(
        select(Textbook).where(Textbook.is_active.is_(True)).order_by(Textbook.grade_label, Textbook.id)
    ).all()
    units = session.scalars(
        select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.grade_label, Unit.sort_order, Unit.id)
    ).all()
    problem_formats = session.scalars(
        select(ProblemFormat).where(ProblemFormat.is_active.is_(True)).order_by(ProblemFormat.id)
    ).all()
    default_unit_id = session.scalar(
        select(Unit.id)
        .join(UnitAllowedFormat, UnitAllowedFormat.unit_id == Unit.id)
        .where(Unit.is_active.is_(True), UnitAllowedFormat.is_active.is_(True))
        .order_by(Unit.grade_label, Unit.sort_order, Unit.id)
    )
    default_format_code = session.scalar(
        select(ProblemFormat.code)
        .join(UnitAllowedFormat, UnitAllowedFormat.problem_format_id == ProblemFormat.id)
        .where(
            UnitAllowedFormat.unit_id == default_unit_id,
            UnitAllowedFormat.is_active.is_(True),
            ProblemFormat.is_active.is_(True),
        )
        .order_by(ProblemFormat.id)
    )

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "app_name": "mathgen-web",
            "subjects": subjects,
            "textbooks": textbooks,
            "units": units,
            "problem_formats": problem_formats,
            "default_unit_id": default_unit_id,
            "default_format_code": default_format_code,
            "unit_metadata": {unit.id: _unit_metadata(unit) for unit in units},
        },
    )


def _unit_metadata(unit: Unit) -> dict:
    try:
        data = json.loads(unit.metadata_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


@router.post("/generate")
async def generate_from_form(request: Request, session: Session = Depends(get_session)) -> RedirectResponse:
    form = await request.form()
    format_weights = {
        key.removeprefix("format_weights[").removesuffix("]"): float(value or 0)
        for key, value in form.multi_items()
        if key.startswith("format_weights[")
    }
    textbook_id = _optional_int(form.get("textbook_id"))
    random_seed = _optional_int(form.get("random_seed"))
    generation_mode = str(form.get("generation_mode") or "selected")
    selected_format_codes = [str(value) for value in form.getlist("selected_format_codes")]
    if generation_mode == "selected" and not selected_format_codes:
        raise HTTPException(status_code=400, detail="직접 선택 모드에서는 문제 형식을 하나 이상 선택해야 합니다.")

    generate_request = GenerateRequest(
        subject_id=int(form.get("subject_id") or 0),
        textbook_id=textbook_id,
        unit_id=int(form.get("unit_id") or 0),
        difficulty_level=int(form.get("difficulty_level") or 3),
        requested_count=int(form.get("requested_count") or 5),
        generation_mode=generation_mode,
        selected_format_codes=selected_format_codes,
        format_weights=format_weights,
        generation_instruction=str(form.get("generation_instruction") or ""),
        random_seed=random_seed,
        explanation_style=str(form.get("explanation_style") or "normal"),
        include_answers=form.get("include_answers") == "on",
        title=str(form.get("title") or "") or None,
    )
    try:
        problem_set = GenerationService(GeminiProvider()).generate(session, generate_request)
    except GenerationServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/problem-sets/{problem_set.id}", status_code=303)


@router.get("/problem-sets", response_class=HTMLResponse)
def problem_set_list(
    request: Request,
    status: str | None = None,
    semester_label: str | None = None,
    unit_id: int | None = None,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    query = select(ProblemSet)
    if status:
        query = query.where(ProblemSet.status == status)
    if unit_id:
        query = query.where(ProblemSet.unit_id == unit_id)
    problem_sets = session.scalars(query.order_by(ProblemSet.created_at.desc()).limit(50)).all()
    units = session.scalars(select(Unit).where(Unit.is_active.is_(True)).order_by(Unit.grade_label, Unit.sort_order)).all()
    if semester_label:
        allowed_unit_ids = {unit.id for unit in units if _unit_metadata(unit).get("semester_label") == semester_label}
        problem_sets = [problem_set for problem_set in problem_sets if problem_set.unit_id in allowed_unit_ids]
    return templates.TemplateResponse(
        request,
        "problem_sets.html",
        {
            "app_name": "mathgen-web",
            "problem_sets": problem_sets,
            "units": units,
            "status_filter": status or "",
            "semester_filter": semester_label or "",
            "unit_filter": unit_id,
            "unit_metadata": {unit.id: _unit_metadata(unit) for unit in units},
        },
    )


@router.get("/problem-sets/{problem_set_id}", response_class=HTMLResponse)
def problem_set_detail(
    problem_set_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    problems = session.scalars(
        select(Problem).where(Problem.problem_set_id == problem_set_id).order_by(Problem.id)
    ).all()
    generation_logs = session.scalars(
        select(GenerationLog).where(GenerationLog.problem_set_id == problem_set_id).order_by(GenerationLog.id)
    ).all()
    assets_by_problem = RenderingService().latest_assets_by_problem(session, [problem.id for problem in problems])
    return templates.TemplateResponse(
        request,
        "problem_set.html",
        {
            "app_name": "mathgen-web",
            "problem_set": problem_set,
            "problems": problems,
            "assets_by_problem": assets_by_problem,
            "generation_logs": generation_logs,
        },
    )


@router.post("/problem-sets/{problem_set_id}/delete")
def delete_problem_set_from_web(problem_set_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    result = delete_problem_set(session, problem_set_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    return RedirectResponse(url="/problem-sets", status_code=303)


@router.get("/problem-sets/{problem_set_id}/worksheet", response_class=HTMLResponse)
def problem_set_worksheet(
    problem_set_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    return _render_print_view(problem_set_id, request, session, "worksheet.html")


@router.get("/problem-sets/{problem_set_id}/answers", response_class=HTMLResponse)
def problem_set_answers(
    problem_set_id: int,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    return _render_print_view(problem_set_id, request, session, "answer_sheet.html")


@router.post("/problem-sets/{problem_set_id}/validate")
def validate_problem_set_from_web(problem_set_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    ValidationService().validate_problem_set(session, problem_set_id)
    return RedirectResponse(url=f"/problem-sets/{problem_set_id}", status_code=303)


@router.post("/problem-sets/{problem_set_id}/render")
def render_problem_set_from_web(problem_set_id: int, session: Session = Depends(get_session)) -> RedirectResponse:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    RenderingService().render_problem_set(session, problem_set_id)
    return RedirectResponse(url=f"/problem-sets/{problem_set_id}", status_code=303)


@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


def _optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(str(value))


def _render_print_view(
    problem_set_id: int,
    request: Request,
    session: Session,
    template_name: str,
) -> HTMLResponse:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        raise HTTPException(status_code=404, detail="Problem set not found")
    problems = session.scalars(
        select(Problem).where(Problem.problem_set_id == problem_set_id).order_by(Problem.id)
    ).all()
    assets_by_problem = RenderingService().latest_assets_by_problem(session, [problem.id for problem in problems])
    return templates.TemplateResponse(
        request,
        template_name,
        {
            "app_name": "mathgen-web",
            "problem_set": problem_set,
            "problems": problems,
            "assets_by_problem": assets_by_problem,
        },
    )
