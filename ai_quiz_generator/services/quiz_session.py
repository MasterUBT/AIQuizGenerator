"""Quiz session state and answer submission."""

from __future__ import annotations

from ai_quiz_generator.domain.question import OPTION_KEYS
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult
from ai_quiz_generator.services.scoring import ExactMatchScorer, Scorer


class QuizSessionError(ValueError):
    """Base class for errors raised by a quiz session."""


class UnknownQuestionError(QuizSessionError):
    """Raised when an answer refers to a question ID that is not in the quiz."""


class InvalidChoiceError(QuizSessionError):
    """Raised when a choice is not A, B, C, or D."""


class DuplicateAnswerError(QuizSessionError):
    """Raised when a question has already been answered."""


class IncompleteQuizError(QuizSessionError):
    """Raised when finish() is called before every question is answered."""


class SessionFinishedError(QuizSessionError):
    """Raised when an answer is submitted after the session has finished."""


class QuizSession:
    """Record one answer per question and grade the quiz when finished.

    Choices are normalized by stripping whitespace and upper-casing, so " b "
    is accepted as "B". Anything else outside A-D is rejected.

    Grading is delegated to a ``Scorer``; ``ExactMatchScorer`` is used when
    none is given.
    """

    def __init__(self, quiz: Quiz, scorer: Scorer | None = None) -> None:
        if not isinstance(quiz, Quiz):
            raise TypeError("quiz must be a Quiz")
        if scorer is None:
            scorer = ExactMatchScorer()
        if not isinstance(scorer, Scorer):
            raise TypeError("scorer must be a Scorer")
        self._quiz = quiz
        self._scorer = scorer
        self._question_ids = [question.id for question in quiz.questions]
        self._answers: dict[int, str] = {}
        self._result: QuizResult | None = None

    @property
    def quiz(self) -> Quiz:
        return self._quiz

    @property
    def answers(self) -> dict[int, str]:
        return dict(self._answers)

    @property
    def unanswered_question_ids(self) -> list[int]:
        return [qid for qid in self._question_ids if qid not in self._answers]

    @property
    def is_finished(self) -> bool:
        return self._result is not None

    def submit_answer(self, question_id: int, choice: str) -> None:
        if self._result is not None:
            raise SessionFinishedError("quiz session is already finished")
        if isinstance(question_id, bool) or question_id not in self._question_ids:
            raise UnknownQuestionError(f"question {question_id} is not in this quiz")
        if question_id in self._answers:
            raise DuplicateAnswerError(f"question {question_id} was already answered")

        self._answers[question_id] = self._normalize_choice(choice)

    def finish(self) -> QuizResult:
        """Grade the quiz. Calling it again returns the same result."""
        if self._result is not None:
            return self._result

        unanswered = self.unanswered_question_ids
        if unanswered:
            raise IncompleteQuizError(
                f"questions not answered yet: {', '.join(map(str, unanswered))}"
            )

        self._result = self._scorer.grade(self._quiz, self._answers)
        return self._result

    @staticmethod
    def _normalize_choice(choice: object) -> str:
        if not isinstance(choice, str):
            raise InvalidChoiceError("choice must be one of A, B, C, or D")
        normalized = choice.strip().upper()
        if normalized not in OPTION_KEYS:
            raise InvalidChoiceError("choice must be one of A, B, C, or D")
        return normalized
