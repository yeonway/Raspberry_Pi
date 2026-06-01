from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class AIProviderError(Exception):
    """Base class for safe provider errors."""


class ProviderConfigurationError(AIProviderError):
    """Raised when a provider cannot run due to missing configuration."""


class ProviderRateLimitError(AIProviderError):
    """Raised when available keys are rate limited or exhausted."""


class ProviderNetworkError(AIProviderError):
    """Raised for network or timeout errors."""


class ProviderResponseError(AIProviderError):
    """Raised when the provider response is malformed or unusable."""


@dataclass(frozen=True)
class StructuredGenerationResult:
    provider: str
    model_name: str
    data: dict[str, Any]
    raw_text: str
    key_id: str | None = None


class AIProvider(ABC):
    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        model_name: str | None = None,
        temperature: float = 0.2,
    ) -> StructuredGenerationResult:
        """Generate JSON data conforming to the requested schema when possible."""
