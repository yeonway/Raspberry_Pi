import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal, create_db_and_tables
from app.main import app
from app.models import ProblemFormat, Subject, Textbook, Unit


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_metadata_endpoints_return_seed_data(client: TestClient) -> None:
    subjects = client.get("/api/subjects")
    textbooks = client.get("/api/textbooks")
    units = client.get("/api/units")
    formats = client.get("/api/problem-formats")

    assert subjects.status_code == 200
    assert textbooks.status_code == 200
    assert units.status_code == 200
    assert formats.status_code == 200

    assert subjects.json()[0]["code"] == "math"
    assert len(textbooks.json()) >= 3
    assert {unit["name"] for unit in units.json()} >= {"소인수분해", "일차방정식", "일차함수", "이차함수", "삼각비"}
    assert {unit["semester_label"] for unit in units.json()} >= {"1학기", "2학기"}
    assert {item["code"] for item in formats.json()} >= {"multiple_choice", "mixed", "graph", "geometry"}


def test_units_can_be_filtered_by_grade_and_semester(client: TestClient) -> None:
    response = client.get("/api/units", params={"grade_label": "중1", "semester_label": "2학기"})

    assert response.status_code == 200
    data = response.json()
    assert data
    assert {item["grade_label"] for item in data} == {"중1"}
    assert {item["semester_label"] for item in data} == {"2학기"}
    assert {item["name"] for item in data} >= {"기본 도형", "자료의 정리와 해석"}


def test_unit_allowed_formats(client: TestClient) -> None:
    units = client.get("/api/units").json()
    linear_equation = next(unit for unit in units if unit["name"] == "일차방정식")

    response = client.get(f"/api/units/{linear_equation['id']}/allowed-formats")

    assert response.status_code == 200
    assert {item["code"] for item in response.json()} == {
        "multiple_choice",
        "short_answer",
        "solution_steps",
        "descriptive",
    }


def test_seed_is_idempotent() -> None:
    create_db_and_tables()
    with SessionLocal() as session:
        before = (
            session.scalar(select(func.count()).select_from(Subject)),
            session.scalar(select(func.count()).select_from(Textbook)),
            session.scalar(select(func.count()).select_from(Unit)),
            session.scalar(select(func.count()).select_from(ProblemFormat)),
        )

    create_db_and_tables()

    with SessionLocal() as session:
        after = (
            session.scalar(select(func.count()).select_from(Subject)),
            session.scalar(select(func.count()).select_from(Textbook)),
            session.scalar(select(func.count()).select_from(Unit)),
            session.scalar(select(func.count()).select_from(ProblemFormat)),
        )

    assert after == before
    assert after[0] >= 1
    assert after[1] >= 3
    assert after[2] >= 27
    assert after[3] >= 10
