"""Validated question domain model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


OPTION_KEYS = frozenset({"A", "B", "C", "D"})


@dataclass(frozen=True, slots=True)
class Question:
    """A single multiple-choice question with exactly four answer options."""

    id: int
    text: str
    options: dict[str, str]
    correct_answer: str
    explanation: str

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0:
            raise ValueError("question id must be a positive integer")

        text = _nonempty_string(self.text, "question text")
        explanation = _nonempty_string(self.explanation, "question explanation")

        if not isinstance(self.options, Mapping):
            raise ValueError("question options must be a mapping")
        if set(self.options) != OPTION_KEYS:
            raise ValueError("question options must contain exactly A, B, C, and D")

        options = {
            key: _nonempty_string(value, f"option {key}")
            for key, value in self.options.items()
        }

        if self.correct_answer not in OPTION_KEYS:
            raise ValueError("correct answer must be one of A, B, C, or D")

        object.__setattr__(self, "text", text)
        object.__setattr__(self, "options", options)
        object.__setattr__(self, "explanation", explanation)


def _nonempty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonempty string")
    return value.strip()

