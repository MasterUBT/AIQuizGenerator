"""An offline provider for practicing with the shared sample quiz."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from ai_quiz_generator.ai.provider import AIProviderConfigurationError


class FixtureProvider:
    """Load sample data while preserving the AIProvider interface."""

    def __init__(self, path: str | Path) -> None:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise AIProviderConfigurationError(
                f"Could not load the sample quiz from {path}."
            ) from exc
        if not isinstance(payload, dict):
            raise AIProviderConfigurationError("The sample quiz must be a JSON object.")
        self._payload = payload

    def generate_quiz(self, source: str, mode: str) -> dict[str, Any]:
        """Return independent sample data; inputs do not change its questions."""
        return deepcopy(self._payload)
