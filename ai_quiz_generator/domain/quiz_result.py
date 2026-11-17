"""Quiz result domain model. Owner: Stina.

Initial agreed shape for the shared starting point. Validation is added
during quiz-engine work on ``feature/quiz-engine``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuizResult:
    """The graded outcome of a finished quiz session."""

    score: int
    total: int
    answers: dict[int, str]
    wrong_question_ids: list[int]
