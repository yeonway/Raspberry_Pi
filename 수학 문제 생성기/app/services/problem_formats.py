from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProblemFormat, UnitAllowedFormat


@dataclass(frozen=True)
class FormatOption:
    code: str
    name: str
    description: str
    default_weight: float
    min_difficulty: int
    max_difficulty: int
    validation_method: str
    rendering_type: str
    supports_auto_validation: bool
    supports_rendering: bool


def get_allowed_format_options(session: Session, unit_id: int) -> list[FormatOption]:
    rows = session.execute(
        select(UnitAllowedFormat, ProblemFormat)
        .join(ProblemFormat, UnitAllowedFormat.problem_format_id == ProblemFormat.id)
        .where(
            UnitAllowedFormat.unit_id == unit_id,
            UnitAllowedFormat.is_active.is_(True),
            ProblemFormat.is_active.is_(True),
        )
        .order_by(ProblemFormat.id)
    ).all()
    return [
        FormatOption(
            code=problem_format.code,
            name=problem_format.name,
            description=problem_format.description,
            default_weight=allowed.default_weight,
            min_difficulty=allowed.min_difficulty,
            max_difficulty=allowed.max_difficulty,
            validation_method=resolve_validation_method(problem_format.code, problem_format.default_validation_method),
            rendering_type=resolve_rendering_type(problem_format.code, problem_format.default_rendering_type),
            supports_auto_validation=problem_format.supports_auto_validation,
            supports_rendering=problem_format.supports_rendering,
        )
        for allowed, problem_format in rows
    ]


def resolve_validation_method(format_code: str, default_method: str) -> str:
    if format_code in {"descriptive", "solution_steps"}:
        return "rubric"
    if format_code in {"proof", "geometry"}:
        return "manual_review"
    return default_method or "manual"


def resolve_rendering_type(format_code: str, default_rendering_type: str) -> str:
    if format_code == "graph":
        return "graph_svg"
    if format_code == "table_interpretation":
        return "html_table"
    if format_code == "geometry":
        return "geometry_svg"
    return default_rendering_type or "none"
