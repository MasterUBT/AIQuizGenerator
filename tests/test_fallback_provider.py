from collections.abc import Mapping
from typing import Any

import pytest

from ai_quiz_generator.ai.fallback_provider import FallbackAIProvider
from ai_quiz_generator.ai.provider import (
    AIProviderRequestError,
    AIProviderResponseError,
)


class StubProvider:
    def __init__(
        self,
        *,
        payload: Mapping[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload or {"topic": "Quiz", "questions": []}
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        self.calls.append((source, mode))
        if self.error is not None:
            raise self.error
        return self.payload


def make_provider(
    primary: StubProvider,
    fallback: StubProvider,
    notices: list[str] | None = None,
) -> FallbackAIProvider:
    return FallbackAIProvider(
        primary,
        fallback,
        primary_name="primary-model",
        fallback_name="fallback-model",
        on_fallback=(notices.append if notices is not None else None),
    )


def test_primary_success_does_not_call_fallback() -> None:
    primary = StubProvider()
    fallback = StubProvider()

    result = make_provider(primary, fallback).generate_quiz("Python", "topic")

    assert result is primary.payload
    assert primary.calls == [("Python", "topic")]
    assert fallback.calls == []


def test_retryable_request_failure_calls_fallback_and_reports_switch() -> None:
    primary = StubProvider(
        error=AIProviderRequestError("temporary failure", retryable=True)
    )
    fallback = StubProvider()
    notices: list[str] = []

    result = make_provider(primary, fallback, notices).generate_quiz("Python", "topic")

    assert result is fallback.payload
    assert fallback.calls == [("Python", "topic")]
    assert notices == ["primary-model failed: temporary failure Trying fallback-model…"]


def test_invalid_model_response_calls_fallback() -> None:
    primary = StubProvider(error=AIProviderResponseError("invalid JSON"))
    fallback = StubProvider()

    result = make_provider(primary, fallback).generate_quiz("Lecture", "lecture")

    assert result is fallback.payload
    assert fallback.calls == [("Lecture", "lecture")]


def test_non_retryable_request_failure_does_not_call_fallback() -> None:
    error = AIProviderRequestError("invalid API key", retryable=False)
    primary = StubProvider(error=error)
    fallback = StubProvider()

    with pytest.raises(AIProviderRequestError) as caught:
        make_provider(primary, fallback).generate_quiz("Python", "topic")

    assert caught.value is error
    assert fallback.calls == []


def test_fallback_failure_is_returned_to_caller() -> None:
    primary = StubProvider(
        error=AIProviderRequestError("primary unavailable", retryable=True)
    )
    fallback_error = AIProviderRequestError("fallback unavailable", retryable=True)
    fallback = StubProvider(error=fallback_error)

    with pytest.raises(AIProviderRequestError) as caught:
        make_provider(primary, fallback).generate_quiz("Python", "topic")

    assert caught.value is fallback_error
