import pytest

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.services.quiz_session import QuizSession
from ai_quiz_generator.services.scoring import ExactMatchScorer, Scorer


class AlwaysCorrectScorer(Scorer):
    """Test double: marks every answered question as correct."""

    def is_correct(self, question: Question, choice: str | None) -> bool:
        return choice is not None


def test_scorer_is_abstract() -> None:
    with pytest.raises(TypeError):
        Scorer()  # type: ignore[abstract]


def test_exact_match_scorer_is_a_scorer() -> None:
    assert isinstance(ExactMatchScorer(), Scorer)


def test_exact_match_counts_missing_answers_as_wrong(sample_quiz: Quiz) -> None:
    result = ExactMatchScorer().grade(sample_quiz, {1: "B"})

    assert result.score == 1
    assert result.wrong_question_ids == [2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_exact_match_rejects_wrong_choice(sample_quiz: Quiz) -> None:
    question = sample_quiz.questions[0]
    wrong = "A" if question.correct_answer != "A" else "B"

    assert ExactMatchScorer().is_correct(question, question.correct_answer)
    assert not ExactMatchScorer().is_correct(question, wrong)
    assert not ExactMatchScorer().is_correct(question, None)


def test_session_uses_exact_match_scorer_by_default(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    for question in sample_quiz.questions:
        session.submit_answer(question.id, "A")

    result = session.finish()

    expected_wrong = [q.id for q in sample_quiz.questions if q.correct_answer != "A"]
    assert result.wrong_question_ids == expected_wrong


def test_session_grades_with_injected_scorer(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz, scorer=AlwaysCorrectScorer())
    for question in sample_quiz.questions:
        session.submit_answer(question.id, "A")

    result = session.finish()

    assert result.score == result.total == 10
    assert result.wrong_question_ids == []


def test_session_rejects_non_scorer(sample_quiz: Quiz) -> None:
    with pytest.raises(TypeError):
        QuizSession(sample_quiz, scorer=object())  # type: ignore[arg-type]
