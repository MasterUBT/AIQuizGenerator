"""Compose and launch the live or offline terminal quiz application."""

import argparse
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from google import genai
from google.genai import types

from ai_quiz_generator.ai.fallback_provider import FallbackAIProvider
from ai_quiz_generator.ai.gemini_provider import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    GeminiProvider,
)
from ai_quiz_generator.ai.provider import AIProvider, AIProviderConfigurationError
from ai_quiz_generator.cli.terminal_ui import TerminalUI
from ai_quiz_generator.infrastructure.fixture_provider import FixtureProvider
from ai_quiz_generator.infrastructure.quiz_exporter import QuizExporter
from ai_quiz_generator.services.quiz_generator import QuizGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "sample_quiz.json"


@dataclass(frozen=True, slots=True)
class GeminiSettings:
    api_key: str
    primary_model: str
    fallback_model: str | None
    timeout: float


def _gemini_settings(
    model_override: str | None,
    fallback_model_override: str | None,
    timeout_override: float | None,
) -> GeminiSettings:
    """Read local settings without replacing exported environment variables."""
    try:
        local = dotenv_values(ENV_FILE)
    except (OSError, UnicodeError) as exc:
        raise AIProviderConfigurationError(
            "Could not read the project's .env file."
        ) from exc

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
        raise AIProviderConfigurationError(
            "GEMINI_MODEL must be a nonempty model name."
        )

    fallback_model = fallback_model_override
    if fallback_model is None:
        fallback_model = os.environ.get(
            "GEMINI_FALLBACK_MODEL",
            local.get("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
        )
    if not fallback_model or not fallback_model.strip():
        raise AIProviderConfigurationError(
            "GEMINI_FALLBACK_MODEL must be a nonempty model name."
        )

    timeout_value: object = timeout_override
    if timeout_value is None:
        timeout_value = os.environ.get(
            "GEMINI_TIMEOUT_SECONDS",
            local.get("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)),
        )
    try:
        timeout = float(timeout_value)
    except (TypeError, ValueError) as exc:
        raise AIProviderConfigurationError(
            "GEMINI_TIMEOUT_SECONDS must be a positive number."
        ) from exc
    if timeout <= 0:
        raise AIProviderConfigurationError(
            "GEMINI_TIMEOUT_SECONDS must be a positive number."
        )

    primary_model = model.strip()
    fallback_model = fallback_model.strip()
    return GeminiSettings(
        api_key=api_key.strip(),
        primary_model=primary_model,
        fallback_model=(fallback_model if fallback_model != primary_model else None),
        timeout=timeout,
    )


def _run_live(
    model_override: str | None,
    fallback_model_override: str | None,
    timeout_override: float | None,
) -> int:
    settings = _gemini_settings(
        model_override,
        fallback_model_override,
        timeout_override,
    )
    client, provider, model_summary = _build_live_provider(settings, print)

    with client:
        print(
            "Gemini mode: quizzes are generated from your topic or lecture. "
            f"Models: {model_summary}. Timeout: {settings.timeout:g}s each."
        )
        TerminalUI(QuizGenerator(provider), QuizExporter()).run()
    return 0


def _build_live_provider(
    settings: GeminiSettings,
    on_fallback: Callable[[str], None] | None = None,
) -> tuple[Any, AIProvider, str]:
    """Create one Gemini client and the configured provider chain."""
    try:
        client = genai.Client(
            api_key=settings.api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
    except Exception as exc:
        raise AIProviderConfigurationError(
            "Could not configure Gemini. Check GEMINI_API_KEY and your environment."
        ) from exc

    provider: AIProvider = GeminiProvider(
        client=client,
        model=settings.primary_model,
        timeout=settings.timeout,
    )
    if settings.fallback_model is not None:
        provider = FallbackAIProvider(
            provider,
            GeminiProvider(
                client=client,
                model=settings.fallback_model,
                timeout=settings.timeout,
            ),
            primary_name=settings.primary_model,
            fallback_name=settings.fallback_model,
            on_fallback=on_fallback,
        )
        model_summary = f"{settings.primary_model}; fallback {settings.fallback_model}"
    else:
        model_summary = settings.primary_model
    return client, provider, model_summary


def main(argv: list[str] | None = None) -> int:
    """Use Gemini by default, with explicit offline practice options."""
    parser = argparse.ArgumentParser(
        description="Generate and take a quiz with Gemini."
    )
    offline = parser.add_mutually_exclusive_group()
    offline.add_argument(
        "--practice",
        action="store_true",
        help="Use the sample quiz without API requests.",
    )
    offline.add_argument(
        "--fixture", type=Path, help="Practice with a different sample quiz JSON file."
    )
    parser.add_argument(
        "--model",
        help="Gemini model name; overrides GEMINI_MODEL in .env or the environment.",
    )
    parser.add_argument(
        "--fallback-model",
        help=(
            "Fallback Gemini model; overrides GEMINI_FALLBACK_MODEL in .env or "
            "the environment."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Per-model request timeout in seconds; overrides GEMINI_TIMEOUT_SECONDS.",
    )
    args = parser.parse_args(argv)
    try:
        if not args.practice and args.fixture is None:
            return _run_live(args.model, args.fallback_model, args.timeout)
        provider = FixtureProvider(args.fixture or DEFAULT_FIXTURE)
    except AIProviderConfigurationError as exc:
        print(f"Could not start quiz: {exc}")
        return 1

    print("Practice mode: every input uses the same sample quiz.")
    TerminalUI(QuizGenerator(provider), QuizExporter()).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
