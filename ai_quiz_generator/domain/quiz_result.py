"""Validated quiz result domain model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ai_quiz_generator.domain.question import OPTION_KEYS


@dataclass(frozen=True, slots=True)
class QuizResult:
    """The graded outcome of a finished quiz session."""

    score: int
    total: int
    answers: dict[int, str]
    wrong_question_ids: list[int]

    def __post_init__(self) -> None:
        if not _is_int(self.total) or self.total <= 0:
            raise ValueError("result total must be a positive integer")
        if not _is_int(self.score) or not 0 <= self.score <= self.total:
            raise ValueError("result score must be an integer between 0 and total")

        if not isinstance(self.answers, Mapping):
            raise ValueError("result answers must be a mapping")
        if any(not _is_int(key) for key in self.answers):
            raise ValueError("result answer keys must be integer question ids")
        if any(value not in OPTION_KEYS for value in self.answers.values()):
            raise ValueError("result answers must be one of A, B, C, or D")

        if not isinstance(self.wrong_question_ids, list):
            raise ValueError("wrong question ids must be a list")
        if any(not _is_int(question_id) for question_id in self.wrong_question_ids):
            raise ValueError("wrong question ids must be integers")
        if len(self.wrong_question_ids) != len(set(self.wrong_question_ids)):
            raise ValueError("wrong question ids must be unique")
        if self.score + len(self.wrong_question_ids) != self.total:
            raise ValueError("score plus wrong answers must equal total")

        object.__setattr__(self, "answers", dict(self.answers))
        object.__setattr__(self, "wrong_question_ids", list(self.wrong_question_ids))


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
