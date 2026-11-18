"""Deterministic quiz grading."""

from __future__ import annotations

from collections.abc import Mapping

from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult


def grade(quiz: Quiz, answers: Mapping[int, str]) -> QuizResult:
    """Compare each answer with its question's correct answer.

    Unanswered questions count as wrong. Wrong question IDs follow quiz order.
    """
    wrong_question_ids = [
        question.id
        for question in quiz.questions
        if answers.get(question.id) != question.correct_answer
    ]
    total = len(quiz.questions)

    return QuizResult(
        score=total - len(wrong_question_ids),
        total=total,
        answers=dict(answers),
        wrong_question_ids=wrong_question_ids,
    )
