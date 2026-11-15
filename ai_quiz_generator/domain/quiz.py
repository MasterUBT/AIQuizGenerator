"""Validated quiz domain model."""

from __future__ import annotations

from dataclasses import dataclass

from ai_quiz_generator.domain.question import Question


QUESTION_COUNT = 10


@dataclass(frozen=True, slots=True)
class Quiz:
    """A quiz containing exactly ten uniquely identified questions."""

    topic: str
    questions: list[Question]

    def __post_init__(self) -> None:
        if not isinstance(self.topic, str) or not self.topic.strip():
            raise ValueError("quiz topic must be a nonempty string")
        if not isinstance(self.questions, list):
            raise ValueError("quiz questions must be a list")
        if len(self.questions) != QUESTION_COUNT:
            raise ValueError(f"quiz must contain exactly {QUESTION_COUNT} questions")
        if any(not isinstance(question, Question) for question in self.questions):
            raise ValueError("every quiz item must be a Question")

        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("quiz question ids must be unique")

        object.__setattr__(self, "topic", self.topic.strip())
        object.__setattr__(self, "questions", list(self.questions))

