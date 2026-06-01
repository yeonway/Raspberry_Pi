from typing import Any

import httpx

from app.config import Settings
from app.kiwoom.token_manager import KiwoomTokenManager
from app.kiwoom.tr_codes import ENDPOINTS


class KiwoomApiError(RuntimeError):
    def __init__(
        self,
        return_code: str | int | None,
        return_msg: str,
        http_status: int,
        internal_message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(return_msg)
        self.return_code = return_code
        self.return_msg = return_msg
        self.http_status = http_status
        self.internal_message = internal_message
        self.payload = payload or {}

    def envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "return_code": self.return_code,
                "return_msg": self.return_msg,
                "http_status": self.http_status,
                "internal_message": self.internal_message,
            }
        }


class KiwoomClient:
    def __init__(self, settings: Settings, token_manager: KiwoomTokenManager) -> None:
        self.settings = settings
        self.token_manager = token_manager

    async def request(
        self,
        tr_code: str,
        body: dict[str, Any] | None = None,
        *,
        cont_yn: str = "N",
        next_key: str = "",
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        token = await self.token_manager.get_token()
        api_endpoint = endpoint or ENDPOINTS.get(tr_code)
        if not api_endpoint:
            raise KiwoomApiError("TR_ENDPOINT_MISSING", "TR endpoint가 설정되지 않았습니다.", 500, tr_code)

        url = f"{self.settings.kiwoom_base_url.rstrip('/')}{api_endpoint}"
        headers = {
            "authorization": f"Bearer {token}",
            "api-id": tr_code,
            "cont-yn": cont_yn,
            "next-key": next_key,
            "content-type": "application/json;charset=UTF-8",
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.kiwoom_timeout_sec) as client:
                response = await client.post(url, json=body or {}, headers=headers)
        except httpx.TimeoutException as exc:
            raise KiwoomApiError("KIWOOM_TIMEOUT", "키움 API 요청 시간이 초과되었습니다.", 504, str(exc)) from exc
        except httpx.HTTPError as exc:
            raise KiwoomApiError("KIWOOM_HTTP_ERROR", "키움 API 네트워크 오류입니다.", 502, str(exc)) from exc

        data = _safe_json(response)
        continuation = {
            "cont_yn": response.headers.get("cont-yn") or response.headers.get("Cont-Yn"),
            "next_key": response.headers.get("next-key") or response.headers.get("Next-Key"),
        }

        return_code = data.get("return_code")
        if response.status_code >= 400 or (return_code is not None and str(return_code) != "0"):
            raise KiwoomApiError(
                return_code=return_code,
                return_msg=str(data.get("return_msg") or "키움 API 호출 실패"),
                http_status=response.status_code,
                internal_message=f"TR={tr_code}, endpoint={api_endpoint}",
                payload=data,
            )

        return {"body": data, "continuation": continuation, "http_status": response.status_code}


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"raw": data}
    except ValueError:
        return {"raw": response.text}
