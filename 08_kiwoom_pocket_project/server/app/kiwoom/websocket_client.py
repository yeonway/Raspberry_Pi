from dataclasses import dataclass
from typing import Any


@dataclass
class RealtimeSubscription:
    codes: list[str]
    fields: list[str]


class KiwoomWebSocketClient:
    """Thin placeholder for Kiwoom realtime WebSocket integration.

    The Android app connects to this bridge server, not directly to Kiwoom.
    A production subscription loop can be added here after Kiwoom realtime
    field mappings are confirmed.
    """

    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self.connected = False

    async def connect(self, access_token: str) -> None:
        _ = access_token
        self.connected = False

    async def subscribe(self, subscription: RealtimeSubscription) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "codes": subscription.codes,
            "fields": subscription.fields,
            "message": "Realtime bridge skeleton. Mock snapshots are served by /ws/realtime.",
        }
