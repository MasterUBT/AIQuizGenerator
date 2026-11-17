"""Gemini implementation of the AI quiz provider boundary."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ai_quiz_generator.ai.provider import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderResponseError,
)


DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_TIMEOUT_SECONDS = 120.0


QUIZ_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "A concise title for the quiz topic.",
        },
        "questions": {
            "type": "array",
            "description": "Exactly ten multiple-choice questions.",
            "minItems": 10,
            "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "minimum": 1},
                    "text": {
                        "type": "string",
                        "description": "The question text.",
                    },
                    "options": {
                        "type": "object",
                        "properties": {
                            "A": {"type": "string"},
                            "B": {"type": "string"},
                            "C": {"type": "string"},
                            "D": {"type": "string"},
                        },
                        "required": ["A", "B", "C", "D"],
                        "additionalProperties": False,
                    },
                    "correct_answer": {
                        "type": "string",
                        "enum": ["A", "B", "C", "D"],
                    },
                    "explanation": {
                        "type": "string",
                        "description": "A concise explanation of the correct answer.",
                    },
                },
                "required": [
                    "id",
                    "text",
                    "options",
                    "correct_answer",
                    "explanation",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["topic", "questions"],
    "additionalProperties": False,
}


class GeminiProvider:
    """Generate structured quiz data using Google's Gemini API."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise AIProviderConfigurationError("Gemini model must be a nonempty string")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise AIProviderConfigurationError("Gemini timeout must be positive")

        self._client = client if client is not None else self._create_client()
        self._model = model.strip()
        self._timeout = float(timeout)

    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        prompt = self._build_prompt(source, mode)

        try:
            response = self._client.interactions.create(
                model=self._model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": QUIZ_RESPONSE_SCHEMA,
                },
                generation_config={
                    "thinking_level": "low",
                    "max_output_tokens": 4096,
                    "temperature": 0.3,
                },
                timeout=self._timeout,
            )
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError("Gemini could not generate the quiz") from exc

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise AIProviderResponseError("Gemini returned an empty response")

        try:
            data = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise AIProviderResponseError("Gemini returned invalid JSON") from exc

        if not isinstance(data, Mapping):
            raise AIProviderResponseError("Gemini response must be a JSON object")
        return data

    @staticmethod
    def _create_client() -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise AIProviderConfigurationError(
                "Gemini support requires the google-genai package"
            ) from exc

        try:
            return genai.Client()
        except Exception as exc:
            raise AIProviderConfigurationError(
                "Gemini client could not be configured; set GEMINI_API_KEY"
            ) from exc

    @staticmethod
    def _build_prompt(source: str, mode: str) -> str:
        if mode == "topic":
            return (
                "Create a clear, educational ten-question multiple-choice quiz "
                f"about this topic: {source}\n"
                "Use distinct questions, plausible distractors, and concise explanations."
            )
        if mode == "lecture":
            return (
                "Create a clear, educational ten-question multiple-choice quiz based "
                "only on the lecture content below. Use distinct questions, plausible "
                f"distractors, and concise explanations.\n\nLecture:\n{source}"
            )
        raise ValueError("mode must be 'topic' or 'lecture'")

