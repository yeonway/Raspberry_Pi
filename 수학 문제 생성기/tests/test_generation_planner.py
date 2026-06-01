import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal, create_db_and_tables
from app.main import app
from app.models import ProblemFormat, Unit, UnitAllowedFormat
from app.services.generation_planner import GenerateRequest, GenerationPlanner
from app.services.problem_formats import get_allowed_format_options


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _unit_id_with_formats(required_codes: set[str]) -> int:
    create_db_and_tables()
    with SessionLocal() as session:
        units = session.scalars(select(Unit).order_by(Unit.id)).all()
        for unit in units:
            rows = session.execute(
                select(ProblemFormat.code)
                .join(UnitAllowedFormat, UnitAllowedFormat.problem_format_id == ProblemFormat.id)
                .where(UnitAllowedFormat.unit_id == unit.id)
            ).all()
            codes = {row[0] for row in rows}
            if required_codes <= codes:
                return unit.id
    raise AssertionError(f"No unit allows required formats: {required_codes}")


def _unit_id_without_format(disallowed_code: str, required_code: str) -> int:
    create_db_and_tables()
    with SessionLocal() as session:
        units = session.scalars(select(Unit).order_by(Unit.id)).all()
        for unit in units:
            rows = session.execute(
                select(ProblemFormat.code)
                .join(UnitAllowedFormat, UnitAllowedFormat.problem_format_id == ProblemFormat.id)
                .where(UnitAllowedFormat.unit_id == unit.id)
            ).all()
            codes = {row[0] for row in rows}
            if required_code in codes and disallowed_code not in codes:
                return unit.id
    raise AssertionError(f"No unit allows {required_code} while rejecting {disallowed_code}")


def _plan(request: GenerateRequest):
    with SessionLocal() as session:
        allowed = get_allowed_format_options(session, request.unit_id)
    return GenerationPlanner().build_plan(request, allowed)


def test_selected_mode_uses_selected_format_for_all_slots() -> None:
    unit_id = _unit_id_with_formats({"multiple_choice"})
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=4,
        generation_mode="selected",
        selected_format_codes=["multiple_choice"],
    )

    plan = _plan(request)

    assert [slot.format_code for slot in plan.problem_slots] == ["multiple_choice"] * 4


def test_random_mode_uses_only_allowed_formats() -> None:
    unit_id = _unit_id_with_formats({"multiple_choice", "short_answer"})
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=10,
        generation_mode="random",
        random_seed=123,
    )

    plan = _plan(request)

    with SessionLocal() as session:
        allowed_codes = {option.code for option in get_allowed_format_options(session, unit_id)}
    assert len(plan.problem_slots) == 10
    assert {slot.format_code for slot in plan.problem_slots} <= allowed_codes


def test_mixed_random_weights_are_converted_to_integer_counts() -> None:
    unit_id = _unit_id_with_formats({"multiple_choice", "short_answer", "descriptive", "graph"})
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=10,
        generation_mode="mixed_random",
        format_weights={
            "multiple_choice": 40,
            "short_answer": 30,
            "descriptive": 20,
            "graph": 10,
        },
    )

    plan = _plan(request)

    assert [slot.format_code for slot in plan.problem_slots] == [
        "multiple_choice",
        "multiple_choice",
        "multiple_choice",
        "multiple_choice",
        "short_answer",
        "short_answer",
        "short_answer",
        "descriptive",
        "descriptive",
        "graph",
    ]


def test_disallowed_requested_format_is_excluded_with_warning() -> None:
    unit_id = _unit_id_without_format("graph", "multiple_choice")
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=3,
        generation_mode="selected",
        selected_format_codes=["graph", "multiple_choice"],
    )

    plan = _plan(request)

    assert [slot.format_code for slot in plan.problem_slots] == ["multiple_choice"] * 3
    assert any("graph" in warning for warning in plan.warnings)


def test_same_seed_produces_same_random_plan() -> None:
    unit_id = _unit_id_with_formats({"multiple_choice", "short_answer"})
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=8,
        generation_mode="random",
        random_seed=77,
    )

    first = _plan(request)
    second = _plan(request)

    assert [slot.format_code for slot in first.problem_slots] == [
        slot.format_code for slot in second.problem_slots
    ]


def test_descriptive_uses_manual_or_rubric_validation() -> None:
    unit_id = _unit_id_with_formats({"descriptive"})
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=1,
        generation_mode="selected",
        selected_format_codes=["descriptive"],
    )

    plan = _plan(request)

    assert plan.problem_slots[0].validation_method in {"manual_review", "rubric"}


def test_graph_uses_graph_rendering_type() -> None:
    unit_id = _unit_id_with_formats({"graph"})
    request = GenerateRequest(
        subject_id=1,
        textbook_id=None,
        unit_id=unit_id,
        difficulty_level=3,
        requested_count=1,
        generation_mode="selected",
        selected_format_codes=["graph"],
    )

    plan = _plan(request)

    assert plan.problem_slots[0].rendering_type.startswith("graph")


def test_generation_plan_api_returns_preview(client: TestClient) -> None:
    unit_id = _unit_id_with_formats({"multiple_choice"})
    response = client.post(
        "/api/generation/plan",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 2,
            "generation_mode": "selected",
            "selected_format_codes": ["multiple_choice"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["requested_count"] == 2
    assert [slot["format_code"] for slot in data["problem_slots"]] == ["multiple_choice", "multiple_choice"]
