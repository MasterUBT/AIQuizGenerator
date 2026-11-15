import pytest

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz


def make_question(question_id: int = 1, **changes: object) -> Question:
    values = {
        "id": question_id,
        "text": f"Question {question_id}?",
        "options": {"A": "One", "B": "Two", "C": "Three", "D": "Four"},
        "correct_answer": "A",
        "explanation": "Because A is correct.",
    }
    values.update(changes)
    return Question(**values)


def make_questions() -> list[Question]:
    return [make_question(question_id) for question_id in range(1, 11)]


def test_question_accepts_valid_data_and_strips_text() -> None:
    question = make_question(text="  What is Python?  ", explanation="  A language.  ")

    assert question.text == "What is Python?"
    assert question.explanation == "A language."


@pytest.mark.parametrize("question_id", [0, -1, True, "1"])
def test_question_rejects_invalid_id(question_id: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        make_question(question_id=question_id)


@pytest.mark.parametrize("field", ["text", "explanation"])
def test_question_rejects_blank_required_text(field: str) -> None:
    with pytest.raises(ValueError, match="nonempty string"):
        make_question(**{field: "   "})


def test_question_requires_exact_option_keys() -> None:
    with pytest.raises(ValueError, match="exactly A, B, C, and D"):
        make_question(options={"A": "One", "B": "Two", "C": "Three"})


def test_question_rejects_blank_option() -> None:
    with pytest.raises(ValueError, match="option D"):
        make_question(options={"A": "One", "B": "Two", "C": "Three", "D": " "})


def test_question_rejects_invalid_correct_answer() -> None:
    with pytest.raises(ValueError, match="correct answer"):
        make_question(correct_answer="E")


def test_question_copies_options() -> None:
    options = {"A": "One", "B": "Two", "C": "Three", "D": "Four"}
    question = make_question(options=options)

    options["A"] = "Changed"

    assert question.options["A"] == "One"


def test_quiz_accepts_exactly_ten_unique_questions() -> None:
    quiz = Quiz(topic="  Python  ", questions=make_questions())

    assert quiz.topic == "Python"
    assert len(quiz.questions) == 10


@pytest.mark.parametrize("count", [9, 11])
def test_quiz_requires_exactly_ten_questions(count: int) -> None:
    with pytest.raises(ValueError, match="exactly 10"):
        Quiz(topic="Python", questions=make_questions()[:count] + (
            [make_question(11)] if count == 11 else []
        ))


def test_quiz_requires_unique_question_ids() -> None:
    questions = make_questions()
    questions[-1] = make_question(1)

    with pytest.raises(ValueError, match="ids must be unique"):
        Quiz(topic="Python", questions=questions)


def test_quiz_rejects_blank_topic() -> None:
    with pytest.raises(ValueError, match="topic"):
        Quiz(topic=" ", questions=make_questions())
