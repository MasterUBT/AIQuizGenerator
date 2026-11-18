"""Deterministic quiz grading."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult


class Scorer(ABC):
    """Grade a quiz from a mapping of question IDs to chosen options.

    Subclasses decide whether a single answer is correct; building the
    ``QuizResult`` is shared so every scorer returns a consistent result.
    """

    def grade(self, quiz: Quiz, answers: Mapping[int, str]) -> QuizResult:
        """Unanswered questions count as wrong. Wrong question IDs follow quiz order."""
        wrong_question_ids = [
            question.id
            for question in quiz.questions
            if not self.is_correct(question, answers.get(question.id))
        ]
        total = len(quiz.questions)

        return QuizResult(
            score=total - len(wrong_question_ids),
            total=total,
            answers=dict(answers),
            wrong_question_ids=wrong_question_ids,
        )

    @abstractmethod
    def is_correct(self, question: Question, choice: str | None) -> bool:
        """Return whether ``choice`` is a correct answer to ``question``."""


class ExactMatchScorer(Scorer):
    """Correct only when the choice equals the question's ``correct_answer``."""

    def is_correct(self, question: Question, choice: str | None) -> bool:
        return choice == question.correct_answer
