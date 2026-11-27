from collections.abc import Mapping
from typing import Any

import pytest

from ai_quiz_generator.ai.provider import AIProviderError
from ai_quiz_generator.services.quiz_generator import (
    InvalidGenerationRequestError,
    QuizGenerationError,
    QuizGenerator,
)


def valid_payload() -> dict[str, Any]:
    return {
        "topic": "Python",
        "questions": [
            {
                "id": question_id,
                "text": f"Question {question_id}?",
                "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
                "correct_answer": "A",
                "explanation": "A is correct.",
            }
            for question_id in range(1, 11)
        ],
    }


class FakeProvider:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[tuple[str, str]] = []

    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        self.calls.append((source, mode))
        return self.payload


class FailingProvider:
    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        raise AIProviderError("unavailable")


@pytest.mark.parametrize("mode", ["topic", "lecture"])
def test_generate_supports_both_modes(mode: str) -> None:
    provider = FakeProvider(valid_payload())
    generator = QuizGenerator(provider)

    quiz = generator.generate("  Python  ", mode)

    assert quiz.topic == "Python"
    assert len(quiz.questions) == 10
    assert provider.calls == [("Python", mode)]


@pytest.mark.parametrize("source", ["", "   ", None])
def test_generate_rejects_empty_source(source: object) -> None:
    with pytest.raises(InvalidGenerationRequestError, match="source"):
        QuizGenerator(FakeProvider(valid_payload())).generate(source, "topic")


@pytest.mark.parametrize("mode", ["file", "TOPIC", "", None])
def test_generate_rejects_unsupported_mode(mode: object) -> None:
    with pytest.raises(InvalidGenerationRequestError, match="mode"):
        QuizGenerator(FakeProvider(valid_payload())).generate("Python", mode)


def test_generate_wraps_provider_failure() -> None:
    with pytest.raises(QuizGenerationError, match="provider failed"):
        QuizGenerator(FailingProvider()).generate("Python", "topic")

def test_sanitized_request_error_reaches_the_caller() -> None:
    from ai_quiz_generator.ai.provider import AIProviderRequestError

    class RejectedProvider:
        def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
            raise AIProviderRequestError("Gemini rejected the API key.")

    with pytest.raises(QuizGenerationError, match="Gemini rejected the API key"):
        QuizGenerator(RejectedProvider()).generate("Python", "topic")


@pytest.mark.parametrize(
    "payload",
    [
        "not an object",
        {"topic": "Python"},
        {"topic": "Python", "questions": []},
    ],
)
def test_generate_rejects_malformed_payload(payload: object) -> None:
    with pytest.raises(QuizGenerationError, match="invalid quiz data"):
        QuizGenerator(FakeProvider(payload)).generate("Python", "topic")


def test_generate_rejects_invalid_question_fields() -> None:
    payload = valid_payload()
    del payload["questions"][0]["explanation"]

    with pytest.raises(QuizGenerationError, match="invalid quiz data"):
        QuizGenerator(FakeProvider(payload)).generate("Python", "topic")


def test_generate_rejects_duplicate_question_ids() -> None:
    payload = valid_payload()
    payload["questions"][-1]["id"] = 1

    with pytest.raises(QuizGenerationError, match="ids must be unique"):
        QuizGenerator(FakeProvider(payload)).generate("Python", "topic")
