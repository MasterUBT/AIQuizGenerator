"""Browser flow tests using Flask's in-process test client."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from io import BytesIO
from typing import Any

import pytest
from flask.testing import FlaskClient

from ai_quiz_generator.ai.provider import AIProviderRequestError
from ai_quiz_generator.web.app import create_app


class RecordingProvider:
    def __init__(
        self,
        payload: dict[str, Any],
        error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def generate_quiz(self, source: str, mode: str) -> Mapping[str, Any]:
        self.calls.append((source, mode))
        if self.error is not None:
            raise self.error
        return deepcopy(self.payload)


@pytest.fixture
def web_client(
    sample_payload: dict[str, Any],
) -> tuple[FlaskClient, RecordingProvider]:
    provider = RecordingProvider(sample_payload)
    app = create_app(provider=provider, testing=True)
    return app.test_client(), provider


def generate_topic(client: FlaskClient, topic: str = "Python") -> str:
    response = client.post(
        "/generate",
        data={"mode": "topic", "topic": topic},
        follow_redirects=False,
    )
    assert response.status_code == 302
    return response.headers["Location"]


def test_start_page_loads(web_client: tuple[FlaskClient, RecordingProvider]) -> None:
    client, provider = web_client

    response = client.get("/")

    assert response.status_code == 200
    assert b"Turn any topic or lecture" in response.data
    assert b"Generate quiz" in response.data
    assert provider.calls == []


def test_topic_generation_displays_quiz_without_answers_or_explanations(
    web_client: tuple[FlaskClient, RecordingProvider],
    sample_payload: dict[str, Any],
) -> None:
    client, provider = web_client

    location = generate_topic(client, "Python OOP")
    response = client.get(location)

    assert provider.calls == [("Python OOP", "topic")]
    assert response.status_code == 200
    assert sample_payload["questions"][0]["text"].encode() in response.data
    assert sample_payload["questions"][0]["explanation"].encode() not in response.data
    assert b"correct_answer" not in response.data


def test_pasted_lecture_is_sent_as_lecture_mode(
    web_client: tuple[FlaskClient, RecordingProvider],
) -> None:
    client, provider = web_client
    lecture = "Classes create objects. Objects have state and behavior."

    response = client.post(
        "/generate",
        data={"mode": "lecture", "lecture": lecture},
    )

    assert response.status_code == 302
    assert provider.calls == [(lecture, "lecture")]


def test_utf8_text_file_is_sent_as_lecture_mode(
    web_client: tuple[FlaskClient, RecordingProvider],
) -> None:
    client, provider = web_client
    lecture = "Python uses indentation to define code blocks."

    response = client.post(
        "/generate",
        data={
            "mode": "file",
            "lecture_file": (BytesIO(lecture.encode()), "lecture.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert provider.calls == [(lecture, "lecture")]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"mode": "topic", "topic": ""}, b"Enter a topic"),
        ({"mode": "lecture", "lecture": ""}, b"cannot be empty"),
        ({"mode": "unknown"}, b"Choose topic"),
    ],
)
def test_invalid_generation_input_is_rejected(
    web_client: tuple[FlaskClient, RecordingProvider],
    data: dict[str, str],
    message: bytes,
) -> None:
    client, provider = web_client

    response = client.post("/generate", data=data)

    assert response.status_code == 400
    assert message in response.data
    assert provider.calls == []


def test_invalid_file_is_rejected(
    web_client: tuple[FlaskClient, RecordingProvider],
) -> None:
    client, provider = web_client

    response = client.post(
        "/generate",
        data={
            "mode": "file",
            "lecture_file": (BytesIO(b"not text"), "lecture.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert b"ending in .txt" in response.data
    assert provider.calls == []


def test_incomplete_submission_returns_to_quiz(
    web_client: tuple[FlaskClient, RecordingProvider],
) -> None:
    client, _ = web_client
    location = generate_topic(client)

    response = client.post(location, data={"question_1": "A"})

    assert response.status_code == 400
    assert b"Answer every question" in response.data
    assert b"Question 10 of 10" in response.data


def test_complete_quiz_shows_score_and_downloads_review(
    web_client: tuple[FlaskClient, RecordingProvider],
    sample_payload: dict[str, Any],
) -> None:
    client, _ = web_client
    location = generate_topic(client)
    token = location.rsplit("/", maxsplit=1)[-1]
    answers = {
        f"question_{question['id']}": question["correct_answer"]
        for question in sample_payload["questions"]
    }
    answers["question_1"] = (
        "B" if sample_payload["questions"][0]["correct_answer"] == "A" else "A"
    )

    response = client.post(location, data=answers, follow_redirects=True)

    assert response.status_code == 200
    assert b"90%" in response.data
    assert b"Needs review" in response.data
    assert sample_payload["questions"][0]["explanation"].encode() in response.data

    download = client.get(f"/result/{token}/review.md")
    assert download.status_code == 200
    assert download.mimetype == "text/markdown"
    assert b"Score: 9/10" in download.data
    assert (
        b'attachment; filename="quiz-review.md"'
        in download.headers["Content-Disposition"].encode()
    )


def test_provider_failure_is_safe_and_stays_on_start_page(
    sample_payload: dict[str, Any],
) -> None:
    provider = RecordingProvider(
        sample_payload,
        error=AIProviderRequestError("Gemini temporarily unavailable"),
    )
    client = create_app(provider=provider, testing=True).test_client()

    response = client.post(
        "/generate",
        data={"mode": "topic", "topic": "Python"},
    )

    assert response.status_code == 400
    assert b"Gemini temporarily unavailable" in response.data
    assert b"Create your quiz" in response.data


def test_unknown_session_returns_to_start_page(
    web_client: tuple[FlaskClient, RecordingProvider],
) -> None:
    client, _ = web_client

    response = client.get("/quiz/not-a-session", follow_redirects=True)

    assert response.status_code == 200
    assert b"expired or could not be found" in response.data
