import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


PROJECT_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = Path(os.getenv("AI_SETTINGS_PATH", str(PROJECT_DIR / "ai_settings.json"))).expanduser()
MAX_SYSTEM_PROMPT_LENGTH = 12000
DEFAULT_SYSTEM_PROMPT = """너는 Minecraft Java/Paper 서버 도우미다.
반드시 한국어로만 답한다.
답변은 1~3문장으로 짧게 한다.
서바이벌 멀티플레이 기준으로 실용적으로 답한다.
저장된 지식이 질문과 관련 있으면 일반 지식보다 우선한다.
저장된 좌표가 관련 있으면 그 좌표를 사용한다.
난이도, 날씨, 시간, 접속자, TPS, 게임모드 질문은 서버 상황 값을 우선 사용한다.
모델, 브리지, 앱이라는 말은 하지 않는다.

기본 정보:
- 다이아몬드는 최신 버전에서 보통 Y=-59 근처가 좋다.
- 철은 Y=16 근처 또는 높은 산에서 잘 나온다.
- 네더라이트 고대 잔해는 보통 Y=15 근처가 좋다.
- 이 서버는 한 명만 자도 밤을 넘길 수 있다.
- Paper Anti-Xray가 켜져 있다."""


def get_ai_settings() -> Dict[str, Any]:
    data = _read_settings()
    prompt = _normalize_prompt(data.get("system_prompt") or DEFAULT_SYSTEM_PROMPT)
    if not prompt:
        prompt = DEFAULT_SYSTEM_PROMPT
    return {
        "system_prompt": prompt,
        "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
        "updated_at": str(data.get("updated_at") or ""),
        "path": str(SETTINGS_PATH),
    }


def ai_system_prompt() -> str:
    return str(get_ai_settings()["system_prompt"])


def update_ai_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = _normalize_prompt(payload.get("system_prompt") or "")
    if not prompt:
        raise ValueError("기본 프롬프트를 입력하세요.")
    if len(prompt) > MAX_SYSTEM_PROMPT_LENGTH:
        raise ValueError(f"기본 프롬프트는 {MAX_SYSTEM_PROMPT_LENGTH}자 이하로 입력하세요.")

    data = {
        "system_prompt": prompt,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_settings(data)
    return get_ai_settings()


def reset_ai_settings() -> Dict[str, Any]:
    data = {
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _write_settings(data)
    return get_ai_settings()


def _read_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_settings(data: Dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = SETTINGS_PATH.with_suffix(SETTINGS_PATH.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(SETTINGS_PATH)


def _normalize_prompt(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
