"""Provider failover without coupling quiz generation to a specific AI model."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ai_quiz_generator.ai.provider import (
    AIProvider,
    AIProviderRequestError,
    AIProviderResponseError,
)


class FallbackAIProvider:
    """Try a secondary provider after a retryable primary failure."""

    def __init__(
        self,
        primary: AIProvider,
        fallback: AIProvider,
        *,
        primary_name: str,
        fallback_name: str,
        on_fallback: Callable[[str], None] | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_name = primary_name
        self._fallback_name = fallback_name
        self._on_fallback = on_fallback

    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        try:
            return self._primary.generate_quiz(source, mode)
        except AIProviderRequestError as exc:
            if not exc.retryable:
                raise
            reason = str(exc)
        except AIProviderResponseError as exc:
            reason = str(exc)

        if self._on_fallback is not None:
            self._on_fallback(
                f"{self._primary_name} failed: {reason} Trying {self._fallback_name}…"
            )
        return self._fallback.generate_quiz(source, mode)
