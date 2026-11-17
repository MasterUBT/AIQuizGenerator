import json
from pathlib import Path
from typing import Any

import pytest

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz


SAMPLE_QUIZ_PATH = Path(__file__).with_name("sample_quiz.json")


def load_sample_payload() -> dict[str, Any]:
    return json.loads(SAMPLE_QUIZ_PATH.read_text(encoding="utf-8"))


def quiz_from_payload(payload: dict[str, Any]) -> Quiz:
    return Quiz(
        topic=payload["topic"],
        questions=[Question(**question) for question in payload["questions"]],
    )


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    return load_sample_payload()


@pytest.fixture
def sample_quiz(sample_payload: dict[str, Any]) -> Quiz:
    return quiz_from_payload(sample_payload)
