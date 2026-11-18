import copy

import pytest

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult
from ai_quiz_generator.services.quiz_session import (
    DuplicateAnswerError,
    IncompleteQuizError,
    InvalidChoiceError,
    QuizSession,
    QuizSessionError,
    SessionFinishedError,
    UnknownQuestionError,
)
from ai_quiz_generator.services.scoring import grade


def wrong_choice(correct: str) -> str:
    return "A" if correct != "A" else "B"


def answer_all(session: QuizSession, choices: dict[int, str]) -> QuizResult:
    for question_id, choice in choices.items():
        session.submit_answer(question_id, choice)
    return session.finish()


def test_all_correct_answers(sample_quiz: Quiz) -> None:
    choices = {q.id: q.correct_answer for q in sample_quiz.questions}

    result = answer_all(QuizSession(sample_quiz), choices)

    assert result.score == 10
    assert result.total == 10
    assert result.wrong_question_ids == []
    assert result.answers == choices


def test_all_wrong_answers(sample_quiz: Quiz) -> None:
    choices = {q.id: wrong_choice(q.correct_answer) for q in sample_quiz.questions}

    result = answer_all(QuizSession(sample_quiz), choices)

    assert result.score == 0
    assert result.wrong_question_ids == [q.id for q in sample_quiz.questions]


def test_mixed_answers(sample_quiz: Quiz) -> None:
    wrong_ids = {2, 5, 9}
    choices = {
        q.id: wrong_choice(q.correct_answer) if q.id in wrong_ids else q.correct_answer
        for q in sample_quiz.questions
    }

    result = answer_all(QuizSession(sample_quiz), choices)

    assert result.score == 7
    assert result.wrong_question_ids == [2, 5, 9]


def test_wrong_ids_follow_quiz_order_not_answer_order(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    for question in reversed(sample_quiz.questions):
        session.submit_answer(question.id, wrong_choice(question.correct_answer))

    result = session.finish()

    assert result.wrong_question_ids == [q.id for q in sample_quiz.questions]


@pytest.mark.parametrize("raw", ["b", " B ", "b\n"])
def test_choices_are_normalized(sample_quiz: Quiz, raw: str) -> None:
    session = QuizSession(sample_quiz)

    session.submit_answer(1, raw)

    assert session.answers == {1: "B"}


@pytest.mark.parametrize("choice", ["E", "", "  ", "AB", "1", None, 1])
def test_invalid_choices_are_rejected(sample_quiz: Quiz, choice: object) -> None:
    session = QuizSession(sample_quiz)

    with pytest.raises(InvalidChoiceError):
        session.submit_answer(1, choice)  # type: ignore[arg-type]

    assert session.answers == {}


@pytest.mark.parametrize("question_id", [0, 11, -1, True, "1", None])
def test_unknown_question_ids_are_rejected(sample_quiz: Quiz, question_id: object) -> None:
    session = QuizSession(sample_quiz)

    with pytest.raises(UnknownQuestionError):
        session.submit_answer(question_id, "A")  # type: ignore[arg-type]


def test_duplicate_answers_are_rejected_and_first_answer_kept(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    session.submit_answer(1, "B")

    with pytest.raises(DuplicateAnswerError):
        session.submit_answer(1, "C")

    assert session.answers == {1: "B"}


def test_finish_before_all_answers_raises(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    session.submit_answer(1, "B")
    session.submit_answer(3, "D")

    with pytest.raises(IncompleteQuizError, match="2, 4, 5, 6, 7, 8, 9, 10"):
        session.finish()

    assert not session.is_finished
    assert session.unanswered_question_ids == [2, 4, 5, 6, 7, 8, 9, 10]


def test_session_can_continue_after_incomplete_finish(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    with pytest.raises(IncompleteQuizError):
        session.finish()

    result = answer_all(session, {q.id: q.correct_answer for q in sample_quiz.questions})

    assert result.score == 10


def test_repeated_finish_returns_same_result(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    first = answer_all(session, {q.id: q.correct_answer for q in sample_quiz.questions})

    assert session.finish() is first
    assert session.is_finished


def test_submit_after_finish_is_rejected(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    answer_all(session, {q.id: q.correct_answer for q in sample_quiz.questions})

    with pytest.raises(SessionFinishedError):
        session.submit_answer(1, "A")


def test_non_sequential_question_ids() -> None:
    ids = [3, 7, 12, 20, 21, 40, 41, 55, 90, 100]
    questions = [
        Question(
            id=question_id,
            text=f"Question {question_id}?",
            options={"A": "One", "B": "Two", "C": "Three", "D": "Four"},
            correct_answer="C",
            explanation="C is correct.",
        )
        for question_id in ids
    ]
    session = QuizSession(Quiz(topic="Numbers", questions=questions))

    with pytest.raises(UnknownQuestionError):
        session.submit_answer(1, "C")

    result = answer_all(session, {qid: "A" if qid in (12, 90) else "C" for qid in ids})

    assert result.score == 8
    assert result.wrong_question_ids == [12, 90]


def test_session_does_not_mutate_quiz(sample_quiz: Quiz) -> None:
    before = copy.deepcopy(sample_quiz)

    answer_all(QuizSession(sample_quiz), {q.id: "A" for q in sample_quiz.questions})

    assert sample_quiz == before


def test_answers_property_returns_copy(sample_quiz: Quiz) -> None:
    session = QuizSession(sample_quiz)
    session.submit_answer(1, "B")

    session.answers[2] = "A"

    assert session.answers == {1: "B"}


def test_session_requires_quiz() -> None:
    with pytest.raises(TypeError):
        QuizSession({"topic": "x", "questions": []})  # type: ignore[arg-type]


def test_all_session_errors_share_base_class() -> None:
    for error in (
        UnknownQuestionError,
        InvalidChoiceError,
        DuplicateAnswerError,
        IncompleteQuizError,
        SessionFinishedError,
    ):
        assert issubclass(error, QuizSessionError)


def test_grade_counts_missing_answers_as_wrong(sample_quiz: Quiz) -> None:
    result = grade(sample_quiz, {1: "B"})

    assert result.score == 1
    assert result.wrong_question_ids == [2, 3, 4, 5, 6, 7, 8, 9, 10]
