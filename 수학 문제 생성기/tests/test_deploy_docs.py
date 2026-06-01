from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deploy_files_exist() -> None:
    required = [
        ROOT / "deploy" / "mathgen.service.example",
        ROOT / "deploy" / "Caddyfile.math.dcout.site.example",
        ROOT / "deploy" / "install_pi.sh",
        ROOT / "deploy" / "backup_db.sh",
            ROOT / "docs" / "deploy_raspberry_pi.md",
            ROOT / "docs" / "operations.md",
            ROOT / "docs" / "api.md",
    ]

    for path in required:
        assert path.exists(), f"Missing deploy artifact: {path}"


def test_deploy_docs_contain_domain_and_internal_port() -> None:
    combined = "\n".join(
        [
            (ROOT / "deploy" / "mathgen.service.example").read_text(encoding="utf-8"),
            (ROOT / "deploy" / "Caddyfile.math.dcout.site.example").read_text(encoding="utf-8"),
            (ROOT / "docs" / "deploy_raspberry_pi.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "operations.md").read_text(encoding="utf-8"),
        ]
    )

    assert "math.dcout.site" in combined
    assert "127.0.0.1:8020" in combined
    assert "mathgen.service" in combined
    assert "/opt/mathgen" in combined


def test_env_example_has_no_real_key() -> None:
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "GEMINI_API_KEYS=" in env_text
    for line in env_text.splitlines():
        if line.startswith("GEMINI_API_KEYS="):
            assert line == "GEMINI_API_KEYS="
        if line.startswith("MATHGEN_GEMINI_API_KEYS="):
            assert line == "MATHGEN_GEMINI_API_KEYS="


def test_systemd_and_caddy_examples_are_scoped() -> None:
    service = (ROOT / "deploy" / "mathgen.service.example").read_text(encoding="utf-8")
    caddy = (ROOT / "deploy" / "Caddyfile.math.dcout.site.example").read_text(encoding="utf-8")

    assert "WorkingDirectory=/opt/mathgen" in service
    assert "EnvironmentFile=/etc/mathgen/mathgen.env" in service
    assert "Restart=always" in service
    assert "RestartSec=5" in service
    assert "reverse_proxy 127.0.0.1:8020" in caddy


def test_readme_and_agents_cover_mvp_operating_rules() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{agents}"

    for required in [
        "Android",
        "MAX_PROBLEMS_PER_GENERATION",
        "AI 이미지 생성",
        "교과서 본문",
        "문제지 출력 화면",
        "정답지 출력 화면",
        "API 키",
    ]:
        assert required in combined
