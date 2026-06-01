from dataclasses import dataclass
from typing import Any, Protocol


class RenderError(Exception):
    """Raised when a payload cannot be rendered deterministically."""


@dataclass(frozen=True)
class RenderOutput:
    rendering_type: str
    status: str
    extension: str | None = None
    file_content: str | bytes | None = None
    content_html: str | None = None
    message: str = ""


class Renderer(Protocol):
    rendering_type: str

    def render(self, payload: dict[str, Any]) -> RenderOutput:
        ...
