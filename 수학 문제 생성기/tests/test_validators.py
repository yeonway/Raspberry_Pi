import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal, create_db_and_tables
from app.main import app
from app.models import Problem, ProblemSet, Subject, Unit, ValidationResult


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _base_ids() -> tuple[int, int]:
    create_db_and_tables()
    with SessionLocal() as session:
        subject_id = session.scalar(select(Subject.id).where(Subject.code == "math"))
        unit_id = session.scalar(select(Unit.id).order_by(Unit.id))
    assert subject_id is not None
    assert unit_id is not None
    return int(subject_id), int(unit_id)


def _create_problem(
    *,
    format_code: str,
    validation_method: str,
    answer_text: str,
    input_schema: dict,
    answer_schema: dict,
    choices: list[str] | None = None,
    rubric: dict | None = None,
    rendering_type: str = "none",
    rendering_payload: dict | None = None,
) -> int:
    subject_id, unit_id = _base_ids()
    with SessionLocal() as session:
        problem_set = ProblemSet(
            title="validator test",
            subject_id=subject_id,
            textbook_id=None,
            unit_id=unit_id,
            difficulty_level=3,
            generation_mode="selected",
            requested_count=1,
            status="generated",
        )
        session.add(problem_set)
        session.commit()
        session.refresh(problem_set)

        problem = Problem(
            problem_set_id=problem_set.id,
            subject_id=subject_id,
            textbook_id=None,
            unit_id=unit_id,
            format_code=format_code,
            difficulty_level=3,
            question_text="validator test question",
            answer_text=answer_text,
            explanation_text="",
            input_schema_json=json.dumps(input_schema),
            answer_schema_json=json.dumps(answer_schema),
            choices_json=json.dumps(choices) if choices is not None else None,
            rubric_json=json.dumps(rubric) if rubric is not None else None,
            rendering_type=rendering_type,
            rendering_payload_json=json.dumps(rendering_payload) if rendering_payload is not None else None,
            validation_method=validation_method,
            validation_status="pending_validation",
            validation_message="",
        )
        session.add(problem)
        session.commit()
        session.refresh(problem)
        return problem.id


def test_arithmetic_validation_success(client: TestClient) -> None:
    problem_id = _create_problem(
        format_code="short_answer",
        validation_method="arithmetic",
        answer_text="5/6",
        input_schema={"expression": "1/2 + 1/3"},
        answer_schema={"value": "5/6"},
    )

    response = client.post(f"/api/validate/problem/{problem_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "auto_validated"


def test_linear_equation_validation_success(client: TestClient) -> None:
    problem_id = _create_problem(
        format_code="short_answer",
        validation_method="linear_equation",
        answer_text="x = 4",
        input_schema={"equation": "x + 3 = 7", "variable": "x"},
        answer_schema={"variable": "x", "value": "4"},
    )

    response = client.post(f"/api/validate/problem/{problem_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "auto_validated"


def test_wrong_answer_validation_failed(client: TestClient) -> None:
    problem_id = _create_problem(
        format_code="short_answer",
        validation_method="arithmetic",
        answer_text="6",
        input_schema={"expression": "2 + 2"},
        answer_schema={"value": "6"},
    )

    response = client.post(f"/api/validate/problem/{problem_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "validation_failed"


def test_multiple_choice_duplicate_choices_detected(client: TestClient) -> None:
    problem_id = _create_problem(
        format_code="multiple_choice",
        validation_method="multiple_choice",
        answer_text="4",
        input_schema={},
        answer_schema={"correct_index": 2},
        choices=["2", "3", "4", "4"],
    )

    response = client.post(f"/api/validate/problem/{problem_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "validation_failed"
    assert "Duplicate" in response.json()["message"]


def test_descriptive_requires_manual_review(client: TestClient) -> None:
    problem_id = _create_problem(
        format_code="descriptive",
        validation_method="rubric",
        answer_text="모범답안",
        input_schema={},
        answer_schema={},
        rubric={"criteria": ["핵심 개념 설명", "계산 과정"]},
    )

    response = client.post(f"/api/validate/problem/{problem_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "manual_review_required"


def test_complex_expression_is_not_supported(client: TestClient) -> None:
    problem_id = _create_problem(
        format_code="short_answer",
        validation_method="linear_equation",
        answer_text="0",
        input_schema={"equation": "x**5 + x + 1 = 0", "variable": "x"},
        answer_schema={"variable": "x", "value": "0"},
    )

    response = client.post(f"/api/validate/problem/{problem_id}")

    assert response.status_code == 200
    assert response.json()["status"] in {"unsupported", "validation_error"}


def test_problem_set_validation_api_stores_results(client: TestClient) -> None:
    first_id = _create_problem(
        format_code="short_answer",
        validation_method="arithmetic",
        answer_text="4",
        input_schema={"expression": "2 + 2"},
        answer_schema={"value": "4"},
    )
    with SessionLocal() as session:
        problem = session.get(Problem, first_id)
        assert problem is not None
        problem_set_id = problem.problem_set_id
        second = Problem(
            problem_set_id=problem_set_id,
            subject_id=problem.subject_id,
            textbook_id=None,
            unit_id=problem.unit_id,
            format_code="descriptive",
            difficulty_level=3,
            question_text="설명하시오.",
            answer_text="모범답안",
            explanation_text="",
            input_schema_json="{}",
            answer_schema_json="{}",
            choices_json=None,
            rubric_json=json.dumps({"criteria": ["설명"]}),
            rendering_type="none",
            rendering_payload_json=None,
            validation_method="rubric",
            validation_status="pending_validation",
            validation_message="",
        )
        session.add(second)
        session.commit()

    response = client.post(f"/api/validate/problem-set/{problem_set_id}")

    assert response.status_code == 200
    assert response.json()["validated_count"] == 2
    with SessionLocal() as session:
        count = len(session.scalars(select(ValidationResult).where(ValidationResult.problem_id == first_id)).all())
    assert count >= 1


def test_validation_timeout_setting_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VALIDATION_TIMEOUT_SECONDS", "0.5")
    get_settings.cache_clear()

    assert get_settings().validation_timeout_seconds == 0.5

    get_settings.cache_clear()
