import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import BASE_DIR
from app.database import SessionLocal, create_db_and_tables
from app.main import app
from app.models import Problem, ProblemSet, RenderedAsset, Subject, Unit


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


def _create_render_problem(rendering_type: str, payload: dict) -> tuple[int, int]:
    subject_id, unit_id = _base_ids()
    with SessionLocal() as session:
        problem_set = ProblemSet(
            title="render test",
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
            format_code="graph" if "graph" in rendering_type else "table_interpretation",
            difficulty_level=3,
            question_text="render test question",
            answer_text="",
            explanation_text="",
            input_schema_json="{}",
            answer_schema_json="{}",
            choices_json=None,
            rubric_json=None,
            rendering_type=rendering_type,
            rendering_payload_json=json.dumps(payload),
            validation_method="manual",
            validation_status="pending_validation",
            validation_message="",
        )
        session.add(problem)
        session.commit()
        session.refresh(problem)
        return problem_set.id, problem.id


def test_linear_graph_svg_is_created(client: TestClient) -> None:
    _, problem_id = _create_render_problem(
        "graph_svg",
        {
            "graph_type": "linear_function",
            "equation": "y = 2*x + 1",
            "x_range": [-5, 5],
            "y_range": [-5, 10],
            "points": [{"x": 0, "y": 1}, {"x": 2, "y": 5}],
            "show_grid": True,
        },
    )

    response = client.post(f"/api/problems/{problem_id}/render")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rendered"
    assert data["asset_url"].startswith("/rendered/")
    path = BASE_DIR / "data" / "rendered" / data["file_path"]
    assert path.exists()
    assert "<svg" in path.read_text(encoding="utf-8")


def test_table_payload_renders_html_table(client: TestClient) -> None:
    _, problem_id = _create_render_problem(
        "html_table",
        {"headers": ["x", "y"], "rows": [[1, 3], [2, 5], [3, 7]]},
    )

    response = client.post(f"/api/problems/{problem_id}/render")

    assert response.status_code == 200
    assert "<table" in response.json()["content_html"]
    assert "<td>5</td>" in response.json()["content_html"]


def test_geometry_rectangle_svg_is_created(client: TestClient) -> None:
    _, problem_id = _create_render_problem("geometry_svg", {"shape": "rectangle", "width": 6, "height": 4, "labels": True})

    response = client.post(f"/api/problems/{problem_id}/render")

    assert response.status_code == 200
    path = BASE_DIR / "data" / "rendered" / response.json()["file_path"]
    assert path.exists()
    assert "<rect" in path.read_text(encoding="utf-8")


def test_bad_payload_is_render_failed(client: TestClient) -> None:
    _, problem_id = _create_render_problem("graph_svg", {"equation": "not allowed !!!"})

    response = client.post(f"/api/problems/{problem_id}/render")

    assert response.status_code == 200
    assert response.json()["status"] == "render_failed"
    assert response.json()["message"]


def test_render_cache_reuses_existing_asset(client: TestClient) -> None:
    _, problem_id = _create_render_problem("html_table", {"headers": ["a"], "rows": [[1]]})

    first = client.post(f"/api/problems/{problem_id}/render").json()
    second = client.post(f"/api/problems/{problem_id}/render").json()

    assert second["id"] == first["id"]
    with SessionLocal() as session:
        rows = session.scalars(select(RenderedAsset).where(RenderedAsset.problem_id == problem_id)).all()
    assert len(rows) == 1


def test_rendered_path_traversal_is_not_served(client: TestClient) -> None:
    response = client.get("/rendered/%2e%2e/README.md")

    assert response.status_code in {400, 404}


def test_problem_set_page_displays_rendered_asset(client: TestClient) -> None:
    problem_set_id, problem_id = _create_render_problem(
        "graph_svg",
        {"equation": "y = x + 1", "x_range": [-2, 2], "y_range": [-2, 4], "points": []},
    )
    render_response = client.post(f"/api/problems/{problem_id}/render")
    assert render_response.status_code == 200

    page = client.get(f"/problem-sets/{problem_set_id}")

    assert page.status_code == 200
    assert "/rendered/" in page.text
