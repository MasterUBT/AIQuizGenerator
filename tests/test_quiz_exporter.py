from pathlib import Path

import pytest

from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult
from ai_quiz_generator.infrastructure.quiz_exporter import QuizExporter, QuizExportError
from ai_quiz_generator.services.quiz_session import QuizSession


def result_with_mistakes(quiz: Quiz, wrong_ids: set[int]) -> QuizResult:
    session = QuizSession(quiz)
    for question in quiz.questions:
        choice = question.correct_answer
        if question.id in wrong_ids:
            choice = "B" if choice == "A" else "A"
        session.submit_answer(question.id, choice)
    return session.finish()


@pytest.mark.parametrize("extension", [".md", ".txt"])
@pytest.mark.parametrize("wrong_ids", [set(), {2}, {2, 5, 9}])
def test_exports_exactly_the_incorrect_answers(
    tmp_path: Path, sample_quiz: Quiz, extension: str, wrong_ids: set[int]
) -> None:
    result = result_with_mistakes(sample_quiz, wrong_ids)
    path = tmp_path / f"review{extension}"

    QuizExporter().export_wrong_answers(sample_quiz, result, str(path))

    content = path.read_text(encoding="utf-8")
    assert f"Score: {result.score}/10" in content
    assert sample_quiz.topic in content
    assert ("No incorrect answers." in content) == (not wrong_ids)
    positions = []
    for question in sample_quiz.questions:
        heading = f"## Question {question.id}\n"
        assert (heading in content) == (question.id in wrong_ids)
        if question.id in wrong_ids:
            selected = result.answers[question.id]
            correct = question.correct_answer
            assert question.text in content
            assert f"**Your answer:** {selected} — {question.options[selected]}" in content
            assert f"**Correct answer:** {correct} — {question.options[correct]}" in content
            assert question.explanation in content
            positions.append(content.index(heading))
    assert positions == sorted(positions)


def test_does_not_overwrite_existing_file(tmp_path: Path, sample_quiz: Quiz) -> None:
    path = tmp_path / "review.md"
    path.write_text("Keep my notes", encoding="utf-8")

    with pytest.raises(QuizExportError, match="already exists"):
        QuizExporter().export_wrong_answers(
            sample_quiz, result_with_mistakes(sample_quiz, {1}), str(path)
        )

    assert path.read_text(encoding="utf-8") == "Keep my notes"


def test_reports_missing_parent_directory(tmp_path: Path, sample_quiz: Quiz) -> None:
    with pytest.raises(QuizExportError, match="folder and permissions"):
        QuizExporter().export_wrong_answers(
            sample_quiz,
            result_with_mistakes(sample_quiz, {1}),
            str(tmp_path / "missing" / "review.md"),
        )


def test_reports_write_permission_error(
    tmp_path: Path, sample_quiz: Quiz, monkeypatch: pytest.MonkeyPatch
) -> None:
    def denied(*args: object, **kwargs: object) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "open", denied)

    with pytest.raises(QuizExportError, match="folder and permissions"):
        QuizExporter().export_wrong_answers(
            sample_quiz, result_with_mistakes(sample_quiz, {1}), str(tmp_path / "review.md")
        )


def test_rejects_unsupported_extension(tmp_path: Path, sample_quiz: Quiz) -> None:
    with pytest.raises(QuizExportError, match=r"\.md or \.txt"):
        QuizExporter().export_wrong_answers(
            sample_quiz, result_with_mistakes(sample_quiz, set()), str(tmp_path / "review.json")
        )


def test_rejects_result_for_unknown_questions_before_writing(
    tmp_path: Path, sample_quiz: Quiz
) -> None:
    result = QuizResult(
        score=9,
        total=10,
        answers={q.id: q.correct_answer for q in sample_quiz.questions},
        wrong_question_ids=[999],
    )
    path = tmp_path / "review.md"

    with pytest.raises(QuizExportError, match="does not match"):
        QuizExporter().export_wrong_answers(sample_quiz, result, str(path))

    assert not path.exists()
