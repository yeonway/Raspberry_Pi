import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal, create_db_and_tables
from app.main import app
from app.models import Problem, ProblemSet, Subject, Unit


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _create_problem_set_for_pages() -> tuple[int, int]:
    create_db_and_tables()
    with SessionLocal() as session:
        subject_id = session.scalar(select(Subject.id).where(Subject.code == "math"))
        unit_id = session.scalar(select(Unit.id).order_by(Unit.id))
        assert subject_id is not None
        assert unit_id is not None

        problem_set = ProblemSet(
            title="출력 화면 테스트",
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
            format_code="short_answer",
            difficulty_level=3,
            question_text="x + 3 = 7일 때 x의 값을 구하여라.",
            answer_text="4",
            explanation_text="양변에서 3을 빼면 x = 4이다.",
            input_schema_json="{}",
            answer_schema_json="{}",
            choices_json=None,
            rubric_json=None,
            rendering_type="none",
            rendering_payload_json=None,
            validation_method="arithmetic",
            validation_status="pending_validation",
            validation_message="",
        )
        session.add(problem)
        session.commit()
        session.refresh(problem)
        return problem_set.id, problem.id


def test_home_page_displays_generation_form(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "문제 생성" in response.text
    assert "generation_mode" in response.text
    assert 'name="semester_label"' in response.text
    assert "1학기" in response.text
    assert "selected_format_codes" in response.text
    assert 'name="selected_format_codes"' in response.text
    assert "checked" in response.text
    assert "계획 미리보기" in response.text
    assert "workspace-grid" in response.text


def test_problem_set_page_links_print_views(client: TestClient) -> None:
    problem_set_id, _ = _create_problem_set_for_pages()

    response = client.get(f"/problem-sets/{problem_set_id}")

    assert response.status_code == 200
    assert f"/problem-sets/{problem_set_id}/worksheet" in response.text
    assert f"/problem-sets/{problem_set_id}/answers" in response.text


def test_problem_set_list_page_renders(client: TestClient) -> None:
    problem_set_id, _ = _create_problem_set_for_pages()

    response = client.get("/problem-sets")

    assert response.status_code == 200
    assert "생성 이력" in response.text
    assert f"/problem-sets/{problem_set_id}" in response.text
    assert "필터 적용" in response.text
    assert f"/problem-sets/{problem_set_id}/delete" in response.text


def test_worksheet_and_answer_sheet_pages_render(client: TestClient) -> None:
    problem_set_id, _ = _create_problem_set_for_pages()

    worksheet = client.get(f"/problem-sets/{problem_set_id}/worksheet")
    answers = client.get(f"/problem-sets/{problem_set_id}/answers")

    assert worksheet.status_code == 200
    assert answers.status_code == 200
    assert "문제지" in worksheet.text
    assert "정답지" in answers.text
    assert "x + 3 = 7" in worksheet.text
    assert "양변에서 3을 빼면" in answers.text


def test_web_delete_problem_set_redirects(client: TestClient) -> None:
    problem_set_id, _ = _create_problem_set_for_pages()

    response = client.post(f"/problem-sets/{problem_set_id}/delete", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/problem-sets"
