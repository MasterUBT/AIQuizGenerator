"""Compose and launch the live or offline terminal quiz application."""

import argparse
import os
from pathlib import Path

from dotenv import dotenv_values
from google import genai

from ai_quiz_generator.ai.gemini_provider import DEFAULT_MODEL, GeminiProvider
from ai_quiz_generator.ai.provider import AIProviderConfigurationError
from ai_quiz_generator.cli.terminal_ui import TerminalUI
from ai_quiz_generator.infrastructure.fixture_provider import FixtureProvider
from ai_quiz_generator.infrastructure.quiz_exporter import QuizExporter
from ai_quiz_generator.services.quiz_generator import QuizGenerator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "sample_quiz.json"


def _gemini_settings(model_override: str | None) -> tuple[str, str]:
    """Read local settings without replacing exported environment variables."""
    try:
        local = dotenv_values(ENV_FILE)
    except (OSError, UnicodeError) as exc:
        raise AIProviderConfigurationError("Could not read the project's .env file.") from exc

    api_key = os.environ.get("GEMINI_API_KEY", local.get("GEMINI_API_KEY")) or ""
    if not api_key.strip():
        raise AIProviderConfigurationError(
            "Set GEMINI_API_KEY in the project's .env file or your environment. "
            "Use --practice to run without an API key."
        )
    model = model_override
    if model is None:
        model = os.environ.get("GEMINI_MODEL", local.get("GEMINI_MODEL", DEFAULT_MODEL))
    if not model or not model.strip():
        raise AIProviderConfigurationError("GEMINI_MODEL must be a nonempty model name.")
    return api_key.strip(), model.strip()


def _run_live(model_override: str | None) -> int:
    api_key, model = _gemini_settings(model_override)
    try:
        client = genai.Client(api_key=api_key)
    except Exception as exc:
        raise AIProviderConfigurationError(
            "Could not configure Gemini. Check GEMINI_API_KEY and your environment."
        ) from exc

    with client:
        provider = GeminiProvider(client=client, model=model)
        print("Gemini mode: quizzes are generated from your topic or lecture.")
        TerminalUI(QuizGenerator(provider), QuizExporter()).run()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Use Gemini by default, with explicit offline practice options."""
    parser = argparse.ArgumentParser(description="Generate and take a quiz with Gemini.")
    offline = parser.add_mutually_exclusive_group()
    offline.add_argument(
        "--practice", action="store_true", help="Use the sample quiz without API requests."
    )
    offline.add_argument(
        "--fixture", type=Path, help="Practice with a different sample quiz JSON file."
    )
    parser.add_argument(
        "--model", help="Gemini model name; overrides GEMINI_MODEL in .env or the environment."
    )
    args = parser.parse_args(argv)
    try:
        if not args.practice and args.fixture is None:
            return _run_live(args.model)
        provider = FixtureProvider(args.fixture or DEFAULT_FIXTURE)
    except AIProviderConfigurationError as exc:
        print(f"Could not start quiz: {exc}")
        return 1

    print("Practice mode: every input uses the same sample quiz.")
    TerminalUI(QuizGenerator(provider), QuizExporter()).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
