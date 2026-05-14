import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


SYSTEM_PROMPT = """너는 학교 익명 커뮤니티의 게시글/댓글 안전 필터다.
입력이 아래 항목 중 하나라도 해당하면 1을 출력한다.

- 욕설 또는 공격적 표현
- 인신공격
- 특정인 비방 또는 모욕
- 혐오 또는 차별 표현
- 성희롱 또는 성적 괴롭힘
- 협박 또는 위협
- 개인정보 노출
- 도배성 분탕 또는 악의적 게시물

문제가 없으면 0을 출력한다.
반드시 0 또는 1 중 한 글자만 출력한다.
설명, 문장, 따옴표, 마침표, 공백을 출력하지 마라."""


@dataclass
class ModerationDecision:
    allowed: bool
    action: str
    rule_flag: int = 0
    ai_flag: int = 0
    final_flag: int = 0
    reasons: List[str] = field(default_factory=list)
    model_name: str = ""
    latency_ms: int = 0


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def input_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class RuleBasedModerationFilter:
    email_pattern = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)
    phone_pattern = re.compile(r"(?:\+?82[-.\s]?)?0?1[016789][-. \s]?\d{3,4}[-. \s]?\d{4}")
    resident_pattern = re.compile(r"\d{6}[-\s]?[1-4]\d{6}")
    long_digit_pattern = re.compile(r"\d{8,}")
    url_pattern = re.compile(r"https?://|www\.", re.I)
    default_blocked_terms = [
        "badword_placeholder",
        "시발",
        "씨발",
        "ㅅㅂ",
        "병신",
        "ㅂㅅ",
        "꺼져",
    ]

    def __init__(self, extra_terms: str = "") -> None:
        self.blocked_terms = self.load_blocked_terms(extra_terms)

    def load_blocked_terms(self, extra_terms: str = "") -> List[str]:
        raw_terms = []
        raw_terms.extend(self.default_blocked_terms)
        raw_terms.extend(os.getenv("COMMUNITY_BLOCKED_TERMS", "").split(","))
        raw_terms.extend(extra_terms.split(","))
        file_path = os.getenv("COMMUNITY_BLOCKED_TERMS_FILE", "").strip()
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    raw_terms.extend(handle.read().splitlines())
            except OSError:
                pass
        terms = []
        for term in raw_terms:
            normalized = self.normalize(term)[1]
            if normalized and normalized not in terms:
                terms.append(normalized)
        return terms

    def normalize(self, content: str) -> Tuple[str, str]:
        lowered = re.sub(r"\s+", " ", content.lower()).strip()
        compact = re.sub(r"[^0-9a-z가-힣]+", "", lowered)
        return lowered, compact

    def check(self, content: str) -> List[str]:
        reasons: List[str] = []
        lowered, compact = self.normalize(content)

        if not lowered:
            reasons.append("empty")
        if len(content) > env_int("COMMUNITY_MODERATION_MAX_CHARS", 1200):
            reasons.append("too_long_for_moderation")
        if self.email_pattern.search(lowered):
            reasons.append("personal_info_email")
        if self.phone_pattern.search(lowered):
            reasons.append("personal_info_phone")
        if self.resident_pattern.search(lowered):
            reasons.append("personal_info_identifier")
        if self.long_digit_pattern.search(lowered):
            reasons.append("personal_info_long_number")
        if len(self.url_pattern.findall(lowered)) >= 3:
            reasons.append("too_many_urls")
        if re.search(r"(.)\1{9,}", compact):
            reasons.append("repeated_characters")
        if re.search(r"(.{2,6})\1{5,}", compact):
            reasons.append("repeated_pattern")
        if len(content) >= 40:
            symbols = sum(1 for ch in content if not ch.isalnum() and not ch.isspace())
            if symbols / max(len(content), 1) > 0.45:
                reasons.append("excessive_symbols")
        for term in self.blocked_terms:
            if term and term in compact:
                reasons.append("blocked_term")
                break

        return reasons


class QwenModerationClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("COMMUNITY_MODERATION_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
        self.model = os.getenv("COMMUNITY_MODERATION_MODEL", "qwen2.5-0.5b-instruct")
        self.timeout = env_int("COMMUNITY_MODERATION_TIMEOUT_SECONDS", 5)

    def moderate(self, content: str) -> Tuple[int, str, int, str]:
        started = time.perf_counter()
        user_prompt = f"입력:\n{content}\n\n출력 규칙:\n0 또는 1만 출력."
        payload: Dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 1,
            "stop": ["\n"],
        }
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            output = str(data["choices"][0]["message"]["content"]).strip()
            latency_ms = int((time.perf_counter() - started) * 1000)
            if output.startswith("1"):
                return 1, "ok", latency_ms, self.model
            if output.startswith("0"):
                return 0, "ok", latency_ms, self.model
            return -1, "invalid_ai_response", latency_ms, self.model
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return -1, f"ai_error:{exc.__class__.__name__}", latency_ms, self.model


class CommunityModerationService:
    def __init__(self, blocked_terms: str = "") -> None:
        self.rule_filter = RuleBasedModerationFilter(blocked_terms)
        self.ai_client = QwenModerationClient()

    def moderate(self, content: str) -> ModerationDecision:
        enabled = env_bool("COMMUNITY_MODERATION_ENABLED", True)
        auto_hide = env_bool("COMMUNITY_MODERATION_AUTO_HIDE", True)
        fail_mode = os.getenv("COMMUNITY_MODERATION_FAIL_MODE", "pending_review").strip() or "pending_review"
        reasons = self.rule_filter.check(content)
        rule_flag = 1 if reasons else 0
        ai_flag = 0
        latency_ms = 0
        model_name = ""

        if enabled:
            ai_flag, ai_reason, latency_ms, model_name = self.ai_client.moderate(
                content[: env_int("COMMUNITY_MODERATION_MAX_CHARS", 1200)]
            )
            if ai_flag < 0:
                reasons.append(ai_reason)

        if ai_flag < 0:
            action = fail_mode if fail_mode in {"allow", "pending_review", "auto_hide"} else "pending_review"
            final_flag = 1 if action != "allow" else rule_flag
        else:
            final_flag = 1 if rule_flag or ai_flag else 0
            if final_flag:
                action = "auto_hide" if auto_hide else "pending_review"
            else:
                action = "allow"

        if rule_flag and not final_flag:
            final_flag = 1
            action = "auto_hide" if auto_hide else "pending_review"

        return ModerationDecision(
            allowed=action == "allow",
            action=action,
            rule_flag=rule_flag,
            ai_flag=max(ai_flag, 0),
            final_flag=final_flag,
            reasons=reasons,
            model_name=model_name,
            latency_ms=latency_ms,
        )
