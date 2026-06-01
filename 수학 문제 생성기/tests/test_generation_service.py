from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal, create_db_and_tables
from app.main import app
from app.models import GenerationLog, Problem, ProblemFormat, ProblemSet, Unit, UnitAllowedFormat
from app.services.ai.base import ProviderConfigurationError, ProviderResponseError, StructuredGenerationResult


class FakeProvider:
    provider_name = "fake-gemini"
    default_model = "fake-model"

    def __init__(self, responses: list[dict[str, Any] | Exception]):
        self.responses = responses
        self.calls = 0

    def status(self) -> dict[str, object]:
        return {
            "provider": self.provider_name,
            "available": True,
            "default_model": self.default_model,
            "registered_key_count": 1,
            "active_key_count": 1,
            "cooldown_key_count": 0,
        }

    def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        model_name: str | None = None,
        temperature: float = 0.2,
    ) -> StructuredGenerationResult:
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return StructuredGenerationResult(
            provider=self.provider_name,
            model_name=model_name or self.default_model,
            data=response,
            raw_text='{"ok": true}',
            key_id="fake-key-id",
        )


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _unit_id_with_format(format_code: str) -> int:
    create_db_and_tables()
    with SessionLocal() as session:
        row = session.execute(
            select(Unit.id)
            .join(UnitAllowedFormat, UnitAllowedFormat.unit_id == Unit.id)
            .join(ProblemFormat, UnitAllowedFormat.problem_format_id == ProblemFormat.id)
            .where(ProblemFormat.code == format_code)
            .order_by(Unit.id)
        ).first()
    assert row is not None
    return int(row[0])


def _problem_payload(format_code: str = "multiple_choice") -> dict[str, Any]:
    return {
        "format_code": format_code,
        "difficulty_level": 3,
        "question_text": "다음 일차방정식을 풀어라: x + 3 = 7",
        "answer_text": "x = 4",
        "explanation_text": "양변에서 3을 빼면 x = 4이다.",
        "input_schema": {"type": "linear_equation", "equation": "x + 3 = 7"},
        "answer_schema": {"type": "value", "variable": "x"},
        "choices": ["x = 2", "x = 3", "x = 4", "x = 5"],
        "correct_index": 2,
        "rubric": {},
        "rendering_type": "none",
        "rendering_payload": {},
        "validation_method": "exact_match",
        "auto_validation_candidate": {"value": 4},
    }


def test_generate_api_saves_mocked_problem_set(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.api as api_routes

    fake = FakeProvider([_problem_payload(), _problem_payload()])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")

    response = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 2,
            "generation_mode": "selected",
            "selected_format_codes": ["multiple_choice"],
            "include_answers": True,
            "explanation_style": "normal",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generated"
    assert len(data["problems"]) == 2
    assert fake.calls == 2

    with SessionLocal() as session:
        problems = session.scalars(
            select(Problem).where(Problem.problem_set_id == data["id"]).order_by(Problem.id)
        ).all()
        logs = session.scalars(
            select(GenerationLog).where(GenerationLog.problem_set_id == data["id"]).order_by(GenerationLog.id)
        ).all()

    assert len(problems) == 2
    assert all(problem.validation_status == "pending_validation" for problem in problems)
    assert len(logs) == 2
    assert all(log.status == "success" for log in logs)
    assert problems[0].choices_json is not None
    assert "x = 4" in problems[0].choices_json


def test_generation_create_api_returns_summary_payload(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.api as api_routes

    fake = FakeProvider([_problem_payload("short_answer")])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("short_answer")

    response = client.post(
        "/api/generation/create",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["short_answer"],
            "title": "API 생성 테스트",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["problem_set_id"] > 0
    assert data["status"] == "generated"
    assert data["requested_count"] == 1
    assert data["generated_count"] == 1
    assert data["problems"][0]["question_text"]

    detail = client.get(f"/api/problem-sets/{data['problem_set_id']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "API 생성 테스트"


def test_generation_create_without_key_returns_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import app.routes.api as api_routes

    class UnavailableProvider(FakeProvider):
        default_model = "fake-model"

        def __init__(self) -> None:
            super().__init__([ProviderConfigurationError("Gemini API key is not configured.")])

        def status(self) -> dict[str, object]:
            return {
                "provider": "gemini",
                "available": False,
                "default_model": self.default_model,
                "registered_key_count": 0,
                "active_key_count": 0,
                "cooldown_key_count": 0,
            }

    monkeypatch.setattr(api_routes, "build_ai_provider", UnavailableProvider)
    unit_id = _unit_id_with_format("short_answer")

    response = client.post(
        "/api/generation/create",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["short_answer"],
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["available"] is False
    assert "not configured" in body["detail"]["error"]


def test_selected_generation_without_format_returns_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import app.routes.api as api_routes

    fake = FakeProvider([_problem_payload()])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")

    response = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": [],
        },
    )

    assert response.status_code == 400
    assert "No selected format" in response.json()["detail"]
    assert fake.calls == 0


def test_generate_api_stores_generation_failed_problem_on_json_failure(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    import app.routes.api as api_routes

    fake = FakeProvider([ProviderResponseError("Gemini response was not valid JSON.")])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")

    response = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["multiple_choice"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert len(data["problems"]) == 1
    assert data["problems"][0]["validation_status"] == "generation_failed"

    with SessionLocal() as session:
        logs = session.scalars(select(GenerationLog).where(GenerationLog.problem_set_id == data["id"])).all()
    assert len(logs) == 1
    assert logs[0].status == "response_error"


def test_problem_set_and_problem_detail_endpoints(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.api as api_routes

    fake = FakeProvider([_problem_payload()])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")
    created = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["multiple_choice"],
        },
    ).json()

    problem_set = client.get(f"/api/problem-sets/{created['id']}")
    problem = client.get(f"/api/problems/{created['problems'][0]['id']}")

    assert problem_set.status_code == 200
    assert problem.status_code == 200
    assert problem.json()["question_text"]

    listing = client.get("/api/problem-sets")
    assert listing.status_code == 200
    assert any(item["id"] == created["id"] for item in listing.json())

    filtered = client.get("/api/problem-sets", params={"status": "generated", "unit_id": unit_id})
    assert filtered.status_code == 200
    assert any(item["id"] == created["id"] for item in filtered.json())

    problems = client.get("/api/problems", params={"problem_set_id": created["id"]})
    assert problems.status_code == 200
    assert len(problems.json()) == 1

    logs = client.get(f"/api/problem-sets/{created['id']}/logs")
    assert logs.status_code == 200
    assert logs.json()[0]["status"] == "success"


def test_problem_set_delete_removes_problem_and_logs(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.api as api_routes

    fake = FakeProvider([_problem_payload()])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")
    created = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["multiple_choice"],
        },
    ).json()

    response = client.delete(f"/api/problem-sets/{created['id']}")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    with SessionLocal() as session:
        assert session.get(ProblemSet, created["id"]) is None
        assert session.get(Problem, created["problems"][0]["id"]) is None
        assert session.scalars(select(GenerationLog).where(GenerationLog.problem_set_id == created["id"])).all() == []


def test_descriptive_generation_is_marked_manual_review(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.api as api_routes

    payload = {
        **_problem_payload("descriptive"),
        "choices": None,
        "rubric": {"criteria": ["핵심 개념", "설명"]},
        "validation_method": "rubric",
    }
    fake = FakeProvider([payload])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("descriptive")

    response = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["descriptive"],
        },
    )

    assert response.status_code == 200
    problem = response.json()["problems"][0]
    assert problem["validation_status"] == "manual_review_required"


def test_generation_logs_do_not_expose_secret(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.api as api_routes

    secret = "secret-key-that-must-not-leak"
    fake = FakeProvider([_problem_payload()])
    monkeypatch.setattr(api_routes, "build_ai_provider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")
    data = client.post(
        "/api/generate",
        json={
            "subject_id": 1,
            "unit_id": unit_id,
            "difficulty_level": 3,
            "requested_count": 1,
            "generation_mode": "selected",
            "selected_format_codes": ["multiple_choice"],
            "generation_instruction": "새 문제를 만들어줘",
        },
    ).json()

    with SessionLocal() as session:
        logs = session.scalars(select(GenerationLog).where(GenerationLog.problem_set_id == data["id"])).all()

    combined = " ".join(f"{log.request_summary} {log.response_summary} {log.error_message}" for log in logs)
    assert secret not in combined
    assert "must-not-leak" not in combined


def test_web_form_redirects_to_result_page(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    import app.routes.web as web_routes

    fake = FakeProvider([_problem_payload()])
    monkeypatch.setattr(web_routes, "GeminiProvider", lambda: fake)
    unit_id = _unit_id_with_format("multiple_choice")

    response = client.post(
        "/generate",
        data={
            "subject_id": "1",
            "unit_id": str(unit_id),
            "difficulty_level": "3",
            "requested_count": "1",
            "generation_mode": "selected",
            "selected_format_codes": "multiple_choice",
            "include_answers": "on",
            "explanation_style": "normal",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    result = client.get(response.headers["location"])
    assert result.status_code == 200
    assert "multiple_choice" in result.text
