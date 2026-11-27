from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ai_quiz_generator.ai.provider import AIProviderError
from ai_quiz_generator.cli.terminal_ui import TerminalUI
from ai_quiz_generator.infrastructure.quiz_exporter import QuizExporter
from ai_quiz_generator.services.quiz_generator import QuizGenerator


class RecordingProvider:
    def __init__(self, payload: dict[str, Any], error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def generate_quiz(self, source: str, mode: str) -> dict[str, Any]:
        self.calls.append((source, mode))
        if self.error is not None:
            raise self.error
        return deepcopy(self.payload)


def correct_answers(payload: dict[str, Any]) -> list[str]:
    return [question["correct_answer"].lower() for question in payload["questions"]]


def run_ui(
    payload: dict[str, Any],
    inputs: list[str],
    *,
    error: Exception | None = None,
) -> tuple[RecordingProvider, str]:
    provider = RecordingProvider(payload, error)
    responses = iter(inputs)
    output: list[str] = []

    def read(prompt: str) -> str:
        try:
            return next(responses)
        except StopIteration:
            pytest.fail(f"Unexpected extra input requested: {prompt}")

    TerminalUI(
        QuizGenerator(provider), QuizExporter(), read=read, write=output.append
    ).run()
    return provider, "\n".join(output)


def test_exit_without_generating(sample_payload: dict[str, Any]) -> None:
    provider, output = run_ui(sample_payload, ["4"])

    assert provider.calls == []
    assert "Goodbye!" in output


@pytest.mark.parametrize("bad_choice", ["", "5", "topic"])
def test_invalid_menu_choice_retries(sample_payload: dict[str, Any], bad_choice: str) -> None:
    provider, output = run_ui(sample_payload, [bad_choice, "4"])

    assert provider.calls == []
    assert "Please choose 1, 2, 3, or 4." in output


def test_topic_flow_displays_questions_and_score(sample_payload: dict[str, Any]) -> None:
    provider, output = run_ui(
        sample_payload, ["1", "  Python  ", *correct_answers(sample_payload), "n", "4"]
    )

    assert provider.calls == [("Python", "topic")]
    assert "Question 1/10:" in output
    assert "Question 10/10:" in output
    first = sample_payload["questions"][0]
    for letter, text in first["options"].items():
        assert f"{letter}. {text}" in output
    assert "Final score: 10/10 (100%)" in output


def test_empty_topic_and_invalid_answers_retry(sample_payload: dict[str, Any]) -> None:
    provider, output = run_ui(
        sample_payload,
        ["1", " ", "Python", "E", "", *correct_answers(sample_payload), "", "4"],
    )

    assert provider.calls == [("Python", "topic")]
    assert "Input cannot be empty." in output
    assert output.count("Please enter A, B, C, or D.") == 2
    assert "Final score: 10/10 (100%)" in output


def test_pasted_lecture_preserves_lines_until_exact_end_marker(
    sample_payload: dict[str, Any],
) -> None:
    provider, output = run_ui(
        sample_payload,
        ["2", "Classes", "", " END ", "Objects", "END",
         *correct_answers(sample_payload), "no", "4"],
    )

    assert provider.calls == [("Classes\n\n END \nObjects", "lecture")]
    assert "Final score: 10/10 (100%)" in output


def test_empty_lecture_retries(sample_payload: dict[str, Any]) -> None:
    provider, output = run_ui(
        sample_payload,
        ["2", " ", "END", "Classes", "END", *correct_answers(sample_payload), "n", "4"],
    )

    assert provider.calls == [("Classes", "lecture")]
    assert "Lecture cannot be empty." in output

@pytest.mark.parametrize(
    "lecture_lines",
    [["/cancel"], ["Some lecture text", "/cancel"], ["END", " /CANCEL "]],
)
def test_lecture_can_be_cancelled_back_to_menu(
    sample_payload: dict[str, Any], lecture_lines: list[str]
) -> None:
    provider, output = run_ui(sample_payload, ["2", *lecture_lines, "4"])

    assert provider.calls == []
    assert "Type /cancel on its own line to return to the menu." in output
    assert "Lecture entry cancelled. Returning to the menu." in output
    assert "Goodbye!" in output


def test_file_input_sends_content_to_generator(
    tmp_path: Path, sample_payload: dict[str, Any]
) -> None:
    path = tmp_path / "lecture.txt"
    path.write_text("Classes\nObjects", encoding="utf-8")
    provider, output = run_ui(
        sample_payload, ["3", str(path), *correct_answers(sample_payload), "n", "4"]
    )

    assert provider.calls == [("Classes\nObjects", "lecture")]
    assert "Final score: 10/10 (100%)" in output


def test_missing_file_returns_to_menu(
    tmp_path: Path, sample_payload: dict[str, Any]
) -> None:
    provider, output = run_ui(
        sample_payload, ["3", str(tmp_path / "missing.txt"), "4"]
    )

    assert provider.calls == []
    assert "File not found:" in output
    assert "Goodbye!" in output


def test_generation_failure_returns_to_menu(sample_payload: dict[str, Any]) -> None:
    _, output = run_ui(
        sample_payload, ["1", "Python", "4"], error=AIProviderError("provider detail")
    )

    assert "Could not start quiz:" in output
    assert "provider detail" not in output
    assert "Goodbye!" in output


def test_malformed_quiz_returns_to_menu(sample_payload: dict[str, Any]) -> None:
    sample_payload["questions"].pop()

    _, output = run_ui(sample_payload, ["1", "Python", "4"])

    assert "invalid quiz data" in output
    assert "Goodbye!" in output


def test_mixed_score_and_export_can_retry_after_failure(
    tmp_path: Path, sample_payload: dict[str, Any]
) -> None:
    choices = correct_answers(sample_payload)
    for index in [0, 3, 6]:
        choices[index] = "b" if choices[index] == "a" else "a"
    existing = tmp_path / "existing.md"
    existing.write_text("Keep", encoding="utf-8")
    destination = tmp_path / "review.md"

    _, output = run_ui(
        sample_payload,
        ["1", "Python", *choices, "maybe", "yes",
         str(existing), str(destination), "4"],
    )

    assert "Final score: 7/10 (70%)" in output
    assert "Please answer yes or no." in output
    assert "already exists" in output
    assert "Review saved to" in output
    assert existing.read_text(encoding="utf-8") == "Keep"
    content = destination.read_text(encoding="utf-8")
    assert "Score: 7/10" in content
    assert content.count("## Question ") == 3


def test_export_can_be_cancelled(sample_payload: dict[str, Any]) -> None:
    _, output = run_ui(
        sample_payload, ["1", "Python", *correct_answers(sample_payload), "y", "", "4"]
    )

    assert "Export cancelled." in output
    assert "Goodbye!" in output


def test_multiple_quizzes_use_fresh_sessions(sample_payload: dict[str, Any]) -> None:
    answers = correct_answers(sample_payload)
    provider, output = run_ui(
        sample_payload,
        ["1", "First", *answers, "n", "1", "Second", *answers, "n", "4"],
    )

    assert provider.calls == [("First", "topic"), ("Second", "topic")]
    assert output.count("Final score: 10/10 (100%)") == 2

@pytest.mark.parametrize("answered", [0, 3, 9])
def test_quiz_can_be_cancelled_at_any_question(
    sample_payload: dict[str, Any], answered: int
) -> None:
    provider, output = run_ui(
        sample_payload,
        ["1", "Python", *correct_answers(sample_payload)[:answered], " /CANCEL ", "4"],
    )

    assert provider.calls == [("Python", "topic")]
    assert f"Question {answered + 1}/10:" in output
    assert "Quiz cancelled. Returning to the menu." in output
    assert "Final score:" not in output
    assert "Goodbye!" in output


def test_new_quiz_can_be_completed_after_cancelling(
    sample_payload: dict[str, Any],
) -> None:
    provider, output = run_ui(
        sample_payload,
        ["1", "First", "/cancel", "1", "Second",
         *correct_answers(sample_payload), "n", "4"],
    )

    assert provider.calls == [("First", "topic"), ("Second", "topic")]
    assert output.count("Final score: 10/10 (100%)") == 1


@pytest.mark.parametrize("exception", [EOFError, KeyboardInterrupt])
@pytest.mark.parametrize("prefix", [[], ["1", "Python"]])
def test_interrupted_input_exits_cleanly(
    sample_payload: dict[str, Any], exception: type[BaseException], prefix: list[str]
) -> None:
    responses = iter(prefix)
    output: list[str] = []

    def read(prompt: str) -> str:
        try:
            return next(responses)
        except StopIteration:
            raise exception()

    TerminalUI(
        QuizGenerator(RecordingProvider(sample_payload)),
        QuizExporter(),
        read=read,
        write=output.append,
    ).run()

    assert "Goodbye!" in output[-1]
