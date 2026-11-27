"""Provider-independent quiz generation service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ai_quiz_generator.ai.provider import AIProvider, AIProviderError, AIProviderRequestError
from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz


SUPPORTED_MODES = frozenset({"topic", "lecture"})
QUIZ_FIELDS = frozenset({"topic", "questions"})
QUESTION_FIELDS = frozenset(
    {"id", "text", "options", "correct_answer", "explanation"}
)


class QuizGenerationError(RuntimeError):
    """Raised when quiz generation fails or returns invalid data."""


class InvalidGenerationRequestError(ValueError):
    """Raised when a caller supplies an invalid generation request."""


class QuizGenerator:
    """Turn provider output into validated quiz domain objects."""

    def __init__(self, provider: AIProvider) -> None:
        if provider is None:
            raise ValueError("provider is required")
        self._provider = provider

    def generate(self, source: str, mode: str) -> Quiz:
        source = self._validate_source(source)
        mode = self._validate_mode(mode)

        try:
            payload = self._provider.generate_quiz(source, mode)
        except AIProviderRequestError as exc:
            raise QuizGenerationError(str(exc)) from exc
        except AIProviderError as exc:
            raise QuizGenerationError("AI provider failed to generate a quiz") from exc

        try:
            return self._parse_quiz(payload)
        except (TypeError, ValueError, KeyError) as exc:
            raise QuizGenerationError(f"AI provider returned invalid quiz data: {exc}") from exc

    @staticmethod
    def _validate_source(source: object) -> str:
        if not isinstance(source, str) or not source.strip():
            raise InvalidGenerationRequestError("source must be a nonempty string")
        return source.strip()

    @staticmethod
    def _validate_mode(mode: object) -> str:
        if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
            raise InvalidGenerationRequestError("mode must be 'topic' or 'lecture'")
        return mode

    @staticmethod
    def _parse_quiz(payload: object) -> Quiz:
        if not isinstance(payload, Mapping):
            raise TypeError("quiz payload must be an object")
        if set(payload) != QUIZ_FIELDS:
            raise ValueError("quiz payload must contain exactly topic and questions")

        raw_questions = payload["questions"]
        if not isinstance(raw_questions, list):
            raise TypeError("questions must be a list")

        questions = [QuizGenerator._parse_question(item) for item in raw_questions]
        return Quiz(topic=payload["topic"], questions=questions)

    @staticmethod
    def _parse_question(payload: object) -> Question:
        if not isinstance(payload, Mapping):
            raise TypeError("each question must be an object")
        if set(payload) != QUESTION_FIELDS:
            raise ValueError(
                "each question must contain exactly id, text, options, "
                "correct_answer, and explanation"
            )

        return Question(
            id=payload["id"],
            text=payload["text"],
            options=payload["options"],
            correct_answer=payload["correct_answer"],
            explanation=payload["explanation"],
        )

