import json
from types import SimpleNamespace
from typing import Any

import pytest

from ai_quiz_generator.ai.gemini_provider import (
    QUIZ_RESPONSE_SCHEMA,
    GeminiProvider,
)
from ai_quiz_generator.ai.provider import (
    AIProviderConfigurationError,
    AIProviderRequestError,
    AIProviderResponseError,
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


class RecordingInteractions:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def make_client(interactions: RecordingInteractions) -> SimpleNamespace:
    return SimpleNamespace(interactions=interactions)


def test_gemini_provider_requests_structured_json() -> None:
    interactions = RecordingInteractions(
        response=SimpleNamespace(output_text=json.dumps(valid_payload()))
    )
    provider = GeminiProvider(
        client=make_client(interactions), model="test-model", timeout=12
    )

    result = provider.generate_quiz("Python", "topic")

    assert result["topic"] == "Python"
    assert interactions.calls == [
        {
            "model": "test-model",
            "input": interactions.calls[0]["input"],
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": QUIZ_RESPONSE_SCHEMA,
            },
            "generation_config": {
                "thinking_level": "low",
                "max_output_tokens": 4096,
                "temperature": 0.3,
            },
            "timeout": 12.0,
        }
    ]
    assert "Python" in interactions.calls[0]["input"]


def test_gemini_provider_uses_lecture_prompt() -> None:
    interactions = RecordingInteractions(
        response=SimpleNamespace(output_text=json.dumps(valid_payload()))
    )
    provider = GeminiProvider(client=make_client(interactions))

    provider.generate_quiz("Classes and objects", "lecture")

    assert "only on the lecture content" in interactions.calls[0]["input"]
    assert "Classes and objects" in interactions.calls[0]["input"]


@pytest.mark.parametrize("output_text", [None, "", "   "])
def test_gemini_provider_rejects_empty_response(output_text: object) -> None:
    client = make_client(
        RecordingInteractions(response=SimpleNamespace(output_text=output_text))
    )

    with pytest.raises(AIProviderResponseError, match="empty response"):
        GeminiProvider(client=client).generate_quiz("Python", "topic")


def test_gemini_provider_rejects_invalid_json() -> None:
    client = make_client(
        RecordingInteractions(response=SimpleNamespace(output_text="not-json"))
    )

    with pytest.raises(AIProviderResponseError, match="invalid JSON"):
        GeminiProvider(client=client).generate_quiz("Python", "topic")


def test_gemini_provider_rejects_non_object_json() -> None:
    client = make_client(
        RecordingInteractions(response=SimpleNamespace(output_text="[]"))
    )

    with pytest.raises(AIProviderResponseError, match="JSON object"):
        GeminiProvider(client=client).generate_quiz("Python", "topic")


def test_gemini_provider_wraps_sdk_error() -> None:
    client = make_client(RecordingInteractions(error=TimeoutError("too slow")))

    with pytest.raises(AIProviderRequestError, match="timed out"):
        GeminiProvider(client=client).generate_quiz("Python", "topic")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"model": ""}, "model"), ({"timeout": 0}, "timeout")],
)
def test_gemini_provider_rejects_invalid_configuration(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(AIProviderConfigurationError, match=message):
        GeminiProvider(client=make_client(RecordingInteractions()), **kwargs)


def test_gemini_provider_rejects_invalid_mode() -> None:
    with pytest.raises(ValueError, match="mode"):
        GeminiProvider(client=make_client(RecordingInteractions())).generate_quiz(
            "Python", "file"
        )


class SDKStatusError(Exception):
    def __init__(self, status: int) -> None:
        super().__init__("remote error including secret-key and private request data")
        self.status_code = status


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (400, "rejected the request"),
        (401, "rejected the API key"),
        (403, "denied access"),
        (404, "model was not found"),
        (429, "quota or rate limit"),
        (503, "temporarily unavailable"),
        (418, "could not generate"),
    ],
)
def test_sdk_status_errors_have_safe_actionable_messages(
    status: int, message: str
) -> None:
    error = SDKStatusError(status)
    client = make_client(RecordingInteractions(error=error))

    with pytest.raises(AIProviderRequestError, match=message) as caught:
        GeminiProvider(client=client).generate_quiz("Python", "topic")

    assert caught.value.__cause__ is error
    assert "secret-key" not in str(caught.value)
    assert "private request data" not in str(caught.value)


def test_public_sdk_error_code_is_translated() -> None:
    from google.genai.errors import ClientError

    error = ClientError(401, {"error": {"message": "invalid secret-key"}})
    client = make_client(RecordingInteractions(error=error))

    with pytest.raises(AIProviderRequestError, match="rejected the API key") as caught:
        GeminiProvider(client=client).generate_quiz("Python", "topic")

    assert "secret-key" not in str(caught.value)


def test_wrapped_network_timeout_is_translated() -> None:
    import httpx

    error = RuntimeError("SDK wrapper with private request data")
    error.__cause__ = httpx.ReadTimeout("secret-key")
    client = make_client(RecordingInteractions(error=error))

    with pytest.raises(AIProviderRequestError, match="timed out") as caught:
        GeminiProvider(client=client).generate_quiz("Python", "topic")

    assert "secret-key" not in str(caught.value)


def test_network_connection_error_is_translated() -> None:
    import httpx

    client = make_client(RecordingInteractions(error=httpx.ConnectError("secret-key")))

    with pytest.raises(AIProviderRequestError, match="internet connection"):
        GeminiProvider(client=client).generate_quiz("Python", "topic")


def test_unexpected_sdk_error_does_not_expose_details() -> None:
    client = make_client(RecordingInteractions(error=RuntimeError("secret-key")))

    with pytest.raises(AIProviderRequestError) as caught:
        GeminiProvider(client=client).generate_quiz("Python", "topic")

    assert str(caught.value) == "Gemini could not generate the quiz."
