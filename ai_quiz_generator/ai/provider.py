"""Provider-independent boundary for AI quiz generation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class AIProviderError(RuntimeError):
    """Raised when an AI provider cannot return usable quiz data."""


class AIProviderRequestError(AIProviderError):
    """A request failure with a sanitized message suitable for the user."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code


class AIProviderConfigurationError(AIProviderError):
    """Raised when an AI provider is not configured correctly."""


class AIProviderResponseError(AIProviderError):
    """Raised when an AI provider returns an unusable response."""


class AIProvider(Protocol):
    """Strategy interface implemented by quiz-generating AI providers."""

    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        """Return structured quiz data for a topic or lecture source."""
        ...
