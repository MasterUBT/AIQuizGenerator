"""Shared contract tests for the Quiz -> QuizSession -> QuizResult boundary."""

import ast
from dataclasses import fields
from pathlib import Path
from typing import Any

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult
from ai_quiz_generator.services.quiz_generator import QuizGenerator
from ai_quiz_generator.services.quiz_session import QuizSession


PACKAGE_DIR = Path(__file__).resolve().parents[1] / "ai_quiz_generator"


class FixtureProvider:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def generate_quiz(self, source: str, mode: str) -> dict[str, Any]:
        return self.payload


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


def test_fixture_passes_quiz_generator_validation(sample_payload: dict[str, Any]) -> None:
    quiz = QuizGenerator(FixtureProvider(sample_payload)).generate("Python", "topic")

    assert [q.id for q in quiz.questions] == list(range(1, 11))


def test_model_fields_match_shared_contract() -> None:
    assert [f.name for f in fields(Question)] == [
        "id", "text", "options", "correct_answer", "explanation",
    ]
    assert [f.name for f in fields(Quiz)] == ["topic", "questions"]
    assert [f.name for f in fields(QuizResult)] == [
        "score", "total", "answers", "wrong_question_ids",
    ]


def test_quiz_to_session_to_result_boundary(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    for question in sample_quiz.questions:
        session.submit_answer(question.id, question.correct_answer.lower())

    result = session.finish()

    assert isinstance(result, QuizResult)
    assert result.score == result.total == 10
    assert result.answers == {q.id: q.correct_answer for q in sample_quiz.questions}


def test_engine_has_no_io_or_external_dependencies() -> None:
    forbidden_modules = ("ai_quiz_generator.cli", "ai_quiz_generator.infrastructure",
                         "ai_quiz_generator.ai", "google")
    files = [
        PACKAGE_DIR / "domain" / "quiz_result.py",
        PACKAGE_DIR / "services" / "quiz_session.py",
        PACKAGE_DIR / "services" / "scoring.py",
    ]

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(forbidden_modules), path
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_modules), path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"print", "input", "open"}, path
