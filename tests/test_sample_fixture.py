"""Shared starting point: the sample fixture loads into the agreed domain models."""

from dataclasses import fields
from typing import Any

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult


def test_fixture_has_ten_complete_questions(sample_payload: dict[str, Any]) -> None:
    questions = sample_payload["questions"]

    assert len(questions) == 10
    assert len({q["id"] for q in questions}) == 10
    for question in questions:
        assert set(question) == {"id", "text", "options", "correct_answer", "explanation"}
        assert set(question["options"]) == {"A", "B", "C", "D"}


def test_fixture_loads_into_domain_models(sample_quiz: Quiz) -> None:
    assert sample_quiz.topic == "Python Basics"
    assert len(sample_quiz.questions) == 10
    assert all(isinstance(q, Question) for q in sample_quiz.questions)


def test_quiz_result_has_agreed_fields() -> None:
    assert [f.name for f in fields(QuizResult)] == [
        "score", "total", "answers", "wrong_question_ids",
    ]
