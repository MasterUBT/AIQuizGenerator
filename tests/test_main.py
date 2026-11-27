import json
from pathlib import Path
from typing import Any

import pytest

from ai_quiz_generator.ai.provider import AIProviderConfigurationError
from ai_quiz_generator.infrastructure.fixture_provider import FixtureProvider
from ai_quiz_generator.main import DEFAULT_FIXTURE, main


def test_fixture_provider_returns_independent_payloads() -> None:
    provider = FixtureProvider(DEFAULT_FIXTURE)
    payload = provider.generate_quiz("Python", "topic")
    payload["questions"].clear()

    assert len(provider.generate_quiz("Lecture", "lecture")["questions"]) == 10


@pytest.mark.parametrize("content", ["not-json", "[]", "null"])
def test_fixture_provider_reports_invalid_json(tmp_path: Path, content: str) -> None:
    path = tmp_path / "quiz.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(AIProviderConfigurationError):
        FixtureProvider(path)


def test_main_reports_missing_fixture(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--fixture", str(tmp_path / "missing.json")]) == 1
    assert "Could not load the sample quiz" in capsys.readouterr().out


def test_main_completes_quiz_and_exports_without_api_key(
    tmp_path: Path,
    sample_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "review.md"
    answers = [q["correct_answer"] for q in sample_payload["questions"]]
    answers[0] = "B" if answers[0] == "A" else "A"
    responses = iter(["1", "Python", *answers, "y", str(path), "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert main(["--practice"]) == 0

    output = capsys.readouterr().out
    assert "Practice mode: every input uses the same sample quiz." in output
    assert "Final score: 9/10 (90%)" in output
    content = path.read_text(encoding="utf-8")
    assert "Score: 9/10" in content
    assert sample_payload["questions"][0]["explanation"] in content
    assert "## Question 2\n" not in content


def test_main_accepts_custom_fixture(
    tmp_path: Path,
    sample_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sample_payload["topic"] = "Custom quiz"
    path = tmp_path / "quiz.json"
    path.write_text(json.dumps(sample_payload), encoding="utf-8")
    responses = iter(["1", "Anything",
                      *[q["correct_answer"] for q in sample_payload["questions"]],
                      "n", "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert main(["--fixture", str(path)]) == 0

    assert "Quiz: Custom quiz" in capsys.readouterr().out

class FakeGeminiClient:
    """Exercise the real provider, parser, UI, and scoring without a network."""

    def __init__(self, payload: dict[str, Any]) -> None:
        from types import SimpleNamespace

        self.payload = payload
        self.calls: list[dict[str, Any]] = []
        self.closed = False
        self.interactions = SimpleNamespace(create=self.create)

    def __enter__(self) -> "FakeGeminiClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def create(self, **kwargs: Any) -> object:
        from types import SimpleNamespace

        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.payload))


@pytest.fixture(autouse=True)
def isolate_local_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    env_file = tmp_path / ".env"
    monkeypatch.setattr("ai_quiz_generator.main.ENV_FILE", env_file)
    for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL"]:
        monkeypatch.delenv(name, raising=False)
    return env_file


@pytest.fixture
def fake_gemini(
    sample_payload: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> tuple[FakeGeminiClient, list[str]]:
    sample_payload["topic"] = "Generated quiz"
    client = FakeGeminiClient(sample_payload)
    keys: list[str] = []

    def create_client(*, api_key: str) -> FakeGeminiClient:
        keys.append(api_key)
        return client

    monkeypatch.setattr("ai_quiz_generator.main.genai.Client", create_client)
    return client, keys


@pytest.mark.parametrize("mode", ["topic", "paste", "file"])
def test_live_assembly_uses_user_input_and_exports_generated_quiz(
    mode: str,
    tmp_path: Path,
    sample_payload: dict[str, Any],
    isolate_local_configuration: Path,
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    isolate_local_configuration.write_text(
        "GEMINI_API_KEY=file-test-key\nGEMINI_MODEL=test-model\n", encoding="utf-8"
    )
    if mode == "topic":
        source = "Photosynthesis"
        prefix = ["1", "", source]
    elif mode == "paste":
        source = "Plants use sunlight.\nLeaves contain chlorophyll."
        prefix = ["2", *source.splitlines(), "END"]
    else:
        source = "Plants use sunlight. Leaves contain chlorophyll."
        lecture = tmp_path / "lecture.txt"
        lecture.write_text(source, encoding="utf-8")
        prefix = ["3", str(lecture)]
    destination = tmp_path / "review.md"
    choices = [q["correct_answer"] for q in sample_payload["questions"]]
    choices[0] = "B" if choices[0] == "A" else "A"
    responses = iter(["0", *prefix, "invalid-answer", *choices, "y", str(destination), "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert main([]) == 0

    client, keys = fake_gemini
    output = capsys.readouterr().out
    assert keys == ["file-test-key"]
    assert len(client.calls) == 1
    assert client.calls[0]["model"] == "test-model"
    assert source in client.calls[0]["input"]
    if mode != "topic":
        assert "only on the lecture content" in client.calls[0]["input"]
    assert client.closed
    assert "Gemini mode:" in output
    assert "Practice mode:" not in output
    assert "Quiz: Generated quiz" in output
    assert "Final score: 9/10 (90%)" in output
    assert "Please enter A, B, C, or D." in output
    assert "file-test-key" not in output
    assert "## Question 1\n" in destination.read_text(encoding="utf-8")


def test_missing_api_key_has_actionable_error(
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 1

    output = capsys.readouterr().out
    assert "Set GEMINI_API_KEY" in output
    assert "--practice" in output
    assert fake_gemini[1] == []


def test_shell_key_overrides_dotenv_without_mutating_environment(
    isolate_local_configuration: Path,
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import os

    isolate_local_configuration.write_text(
        'GEMINI_API_KEY="file-test-key"\n', encoding="utf-8"
    )
    monkeypatch.setenv("GEMINI_API_KEY", "shell-test-key")
    monkeypatch.setattr("builtins.input", lambda prompt: "4")

    assert main([]) == 0

    assert fake_gemini[1] == ["shell-test-key"]
    assert os.environ["GEMINI_API_KEY"] == "shell-test-key"
    output = capsys.readouterr().out
    assert "shell-test-key" not in output
    assert "file-test-key" not in output


@pytest.mark.parametrize(
    ("file_model", "shell_model", "arguments", "expected"),
    [
        ("file-model", None, [], "file-model"),
        ("file-model", "shell-model", [], "shell-model"),
        ("file-model", "shell-model", ["--model", "cli-model"], "cli-model"),
    ],
)
def test_model_configuration_precedence(
    file_model: str,
    shell_model: str | None,
    arguments: list[str],
    expected: str,
    sample_payload: dict[str, Any],
    isolate_local_configuration: Path,
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolate_local_configuration.write_text(
        f"GEMINI_API_KEY=test-key\nGEMINI_MODEL={file_model}\n", encoding="utf-8"
    )
    if shell_model is not None:
        monkeypatch.setenv("GEMINI_MODEL", shell_model)
    responses = iter(["1", "Topic",
                      *[q["correct_answer"] for q in sample_payload["questions"]],
                      "n", "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert main(arguments) == 0

    assert fake_gemini[0].calls[0]["model"] == expected


def test_invalid_env_encoding_reports_configuration_error(
    isolate_local_configuration: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    isolate_local_configuration.write_bytes(b"\xff\xfe")

    assert main([]) == 1

    assert "Could not read the project's .env file." in capsys.readouterr().out


def test_client_configuration_errors_do_not_expose_secrets(
    isolate_local_configuration: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    isolate_local_configuration.write_text("GEMINI_API_KEY=test-secret\n", encoding="utf-8")

    def broken_client(**kwargs: object) -> None:
        raise RuntimeError("sensitive detail: test-secret")

    monkeypatch.setattr("ai_quiz_generator.main.genai.Client", broken_client)

    assert main([]) == 1

    output = capsys.readouterr().out
    assert "Could not configure Gemini" in output
    assert "test-secret" not in output


def test_practice_skips_gemini_and_dotenv(
    isolate_local_configuration: Path,
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    isolate_local_configuration.write_bytes(b"\xff\xfe")
    monkeypatch.setattr("builtins.input", lambda prompt: "4")

    assert main(["--practice"]) == 0

    assert fake_gemini[1] == []


def test_live_generation_failure_returns_to_menu_and_closes_client(
    isolate_local_configuration: Path,
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    isolate_local_configuration.write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")

    def failure(**kwargs: Any) -> object:
        raise TimeoutError("sensitive remote detail")

    client = fake_gemini[0]
    client.interactions.create = failure
    responses = iter(["1", "Photosynthesis", "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert main([]) == 0

    output = capsys.readouterr().out
    assert "Could not start quiz:" in output
    assert "Goodbye!" in output
    assert "sensitive remote detail" not in output
    assert "Practice mode:" not in output
    assert client.closed

def test_rejected_key_is_explained_in_terminal_without_leaking_sdk_details(
    isolate_local_configuration: Path,
    fake_gemini: tuple[FakeGeminiClient, list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    isolate_local_configuration.write_text("GEMINI_API_KEY=test-key\n", encoding="utf-8")

    class RejectedKeyError(Exception):
        status_code = 401

    def rejected(**kwargs: Any) -> object:
        raise RejectedKeyError("request URL included test-key")

    client = fake_gemini[0]
    client.interactions.create = rejected
    responses = iter(["1", "Claude orchestration", "4"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    assert main([]) == 0

    output = capsys.readouterr().out
    assert "Gemini rejected the API key." in output
    assert "Check GEMINI_API_KEY in .env or your environment." in output
    assert "test-key" not in output
    assert "request URL" not in output
    assert "Goodbye!" in output
