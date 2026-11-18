from dataclasses import FrozenInstanceError

import pytest

from ai_quiz_generator.domain.quiz_result import QuizResult


def make_result(**changes: object) -> QuizResult:
    values = {
        "score": 1,
        "total": 2,
        "answers": {1: "A", 2: "B"},
        "wrong_question_ids": [2],
    }
    values.update(changes)
    return QuizResult(**values)


def test_result_accepts_valid_data() -> None:
    result = make_result()

    assert result.score == 1
    assert result.total == 2
    assert result.answers == {1: "A", 2: "B"}
    assert result.wrong_question_ids == [2]


def test_result_is_immutable() -> None:
    result = make_result()

    with pytest.raises(FrozenInstanceError):
        result.score = 2  # type: ignore[misc]


def test_result_copies_collections() -> None:
    answers = {1: "A", 2: "B"}
    wrong = [2]
    result = make_result(answers=answers, wrong_question_ids=wrong)

    answers[1] = "D"
    wrong.append(1)

    assert result.answers == {1: "A", 2: "B"}
    assert result.wrong_question_ids == [2]


@pytest.mark.parametrize("total", [0, -1, True, "2"])
def test_result_rejects_invalid_total(total: object) -> None:
    with pytest.raises(ValueError, match="total"):
        make_result(total=total)


@pytest.mark.parametrize("score", [-1, 3, True, "1"])
def test_result_rejects_invalid_score(score: object) -> None:
    with pytest.raises(ValueError, match="score"):
        make_result(score=score)


def test_result_rejects_invalid_answer_choice() -> None:
    with pytest.raises(ValueError, match="A, B, C, or D"):
        make_result(answers={1: "A", 2: "E"})


def test_result_rejects_non_integer_answer_keys() -> None:
    with pytest.raises(ValueError, match="integer question ids"):
        make_result(answers={"1": "A", 2: "B"})


def test_result_rejects_duplicate_wrong_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        make_result(score=0, wrong_question_ids=[2, 2])


def test_result_requires_score_and_wrong_ids_to_match_total() -> None:
    with pytest.raises(ValueError, match="equal total"):
        make_result(score=2, wrong_question_ids=[2])
