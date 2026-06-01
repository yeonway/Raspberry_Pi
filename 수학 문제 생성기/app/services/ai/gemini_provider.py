import json
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.ai.base import (
    AIProviderError,
    AIProvider,
    ProviderConfigurationError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderResponseError,
    StructuredGenerationResult,
)
from app.services.ai.key_pool import APIKeyRecord, NoAvailableKeyError, RoundRobinKeyPool


GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(AIProvider):
    provider_name = "gemini"

    def __init__(
        self,
        settings: Settings | None = None,
        key_pool: RoundRobinKeyPool | None = None,
        client: httpx.Client | None = None,
    ):
        self.settings = settings or get_settings()
        self.default_model = self.settings.gemini_model_default
        self.max_retries = self.settings.ai_max_retries
        self.timeout_seconds = self.settings.ai_request_timeout_seconds
        self.key_pool = key_pool or self._build_env_key_pool(self.settings)
        self._client = client

    @classmethod
    def _build_env_key_pool(cls, settings: Settings) -> RoundRobinKeyPool:
        secrets = [key.strip() for key in settings.gemini_api_keys.split(",") if key.strip()]
        records = [
            APIKeyRecord(key_id=f"gemini-env-{index}", provider=cls.provider_name, secret=secret)
            for index, secret in enumerate(secrets, start=1)
        ]
        return RoundRobinKeyPool(records, cooldown_seconds=settings.ai_key_cooldown_seconds)

    def status(self) -> dict[str, Any]:
        summary = self.key_pool.summary()
        return {
            "provider": self.provider_name,
            "available": summary["active_key_count"] > 0,
            "default_model": self.default_model,
            **summary,
        }

    def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        model_name: str | None = None,
        temperature: float = 0.2,
    ) -> StructuredGenerationResult:
        if self.key_pool.summary()["registered_key_count"] == 0:
            raise ProviderConfigurationError("Gemini API key is not configured.")

        last_error: AIProviderError | None = None
        attempts = min(self.max_retries, max(1, self.key_pool.summary()["registered_key_count"]))
        for _ in range(attempts):
            try:
                key = self.key_pool.get_next_key()
            except NoAvailableKeyError as exc:
                raise ProviderRateLimitError(str(exc)) from exc

            try:
                result = self._call_gemini(key, prompt, schema, model_name or self.default_model, temperature)
            except ProviderRateLimitError as exc:
                self.key_pool.mark_rate_limited(key.key_id)
                last_error = exc
                continue
            except ProviderNetworkError as exc:
                self.key_pool.mark_error(key.key_id)
                last_error = exc
                continue
            except ProviderResponseError:
                self.key_pool.mark_error(key.key_id)
                raise
            except Exception as exc:
                self.key_pool.mark_error(key.key_id)
                raise ProviderResponseError("Unexpected Gemini provider error.") from exc

            self.key_pool.mark_success(key.key_id)
            return result

        if last_error is not None:
            raise last_error
        raise ProviderRateLimitError("Gemini request failed before a key could be used.")

    def _call_gemini(
        self,
        key: APIKeyRecord,
        prompt: str,
        schema: dict[str, Any],
        model_name: str,
        temperature: float,
    ) -> StructuredGenerationResult:
        url = f"{GEMINI_API_BASE_URL}/models/{model_name}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }

        try:
            if self._client is not None:
                response = self._client.post(url, params={"key": key.secret}, json=payload)
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, params={"key": key.secret}, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderNetworkError("Gemini request timed out.") from exc
        except httpx.RequestError as exc:
            raise ProviderNetworkError("Gemini network request failed.") from exc

        if response.status_code in {429, 503}:
            raise ProviderRateLimitError(f"Gemini returned retryable status {response.status_code}.")
        if response.status_code >= 400:
            safe_message = _extract_safe_error_message(response)
            raise ProviderResponseError(f"Gemini returned status {response.status_code}: {safe_message}")

        raw_text = _extract_text(response)
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("Gemini response was not valid JSON.") from exc

        if not isinstance(data, dict):
            raise ProviderResponseError("Gemini JSON response was not an object.")

        return StructuredGenerationResult(
            provider=self.provider_name,
            model_name=model_name,
            data=data,
            raw_text=raw_text,
            key_id=key.key_id,
        )


def _extract_text(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("Gemini response body was not JSON.") from exc

    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text_parts = [part["text"] for part in parts if "text" in part]
        return "\n".join(text_parts).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderResponseError("Gemini response did not contain text content.") from exc


def _extract_safe_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return "Non-JSON error response."

    message = payload.get("error", {}).get("message", "No provider message.")
    return str(message)[:500]
