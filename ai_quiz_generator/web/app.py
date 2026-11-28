"""Flask application that reuses the existing quiz services."""

from __future__ import annotations

import atexit
import os
import secrets
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from ai_quiz_generator.ai.provider import AIProvider
from ai_quiz_generator.infrastructure.quiz_exporter import QuizExporter
from ai_quiz_generator.main import _build_live_provider, _gemini_settings
from ai_quiz_generator.services.quiz_generator import (
    InvalidGenerationRequestError,
    QuizGenerationError,
    QuizGenerator,
)
from ai_quiz_generator.services.quiz_session import QuizSession, QuizSessionError
from ai_quiz_generator.web.session_store import QuizSessionStore

MAX_TOPIC_CHARACTERS = 300
MAX_LECTURE_CHARACTERS = 100_000
MAX_UPLOAD_BYTES = 1_000_000


class WebInputError(ValueError):
    """Browser input cannot be used to generate a quiz."""


def create_app(
    provider: AIProvider | None = None,
    *,
    store: QuizSessionStore | None = None,
    testing: bool = False,
) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES + 64_000,
        SEND_FILE_MAX_AGE_DEFAULT=0,
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32),
        TEMPLATES_AUTO_RELOAD=True,
        TESTING=testing,
    )

    if provider is None:
        settings = _gemini_settings(None, None, None)
        client, provider, model_summary = _build_live_provider(
            settings,
            lambda message: flash(message, "warning"),
        )
        app.extensions["gemini_client"] = client
        app.extensions["gemini_model_summary"] = model_summary
        atexit.register(client.close)
    else:
        app.extensions["gemini_model_summary"] = "test provider"

    generator = QuizGenerator(provider)
    exporter = QuizExporter()
    session_store = store or QuizSessionStore()
    app.extensions["quiz_store"] = session_store

    @app.get("/")
    def index() -> str:
        return render_template("index.html", selected_mode="topic")

    @app.post("/generate")
    def generate_quiz() -> tuple[str, int] | Response:
        selected_mode = request.form.get("mode", "topic")
        try:
            source, generation_mode = _read_generation_source(selected_mode)
            quiz = generator.generate(source, generation_mode)
        except (
            WebInputError,
            InvalidGenerationRequestError,
            QuizGenerationError,
        ) as exc:
            return (
                render_template(
                    "index.html",
                    error=str(exc),
                    selected_mode=selected_mode,
                    form_values=request.form,
                ),
                400,
            )

        token = session_store.create(quiz)
        return redirect(url_for("quiz_view", token=token))

    @app.get("/quiz/<token>")
    def quiz_view(token: str) -> str | Response:
        state = session_store.get(token)
        if state is None:
            flash(
                "That quiz expired or could not be found. Generate a new quiz.", "error"
            )
            return redirect(url_for("index"))
        return render_template(
            "quiz.html",
            quiz=state.quiz,
            token=token,
            selections={},
        )

    @app.post("/quiz/<token>")
    def submit_quiz(token: str) -> tuple[str, int] | Response:
        state = session_store.get(token)
        if state is None:
            flash(
                "That quiz expired or could not be found. Generate a new quiz.", "error"
            )
            return redirect(url_for("index"))

        selections = {
            question.id: request.form.get(f"question_{question.id}", "").strip()
            for question in state.quiz.questions
        }
        missing = [
            question.id
            for question in state.quiz.questions
            if not selections[question.id]
        ]
        if missing:
            return (
                render_template(
                    "quiz.html",
                    quiz=state.quiz,
                    token=token,
                    selections=selections,
                    error="Answer every question before submitting your quiz.",
                ),
                400,
            )

        session = QuizSession(state.quiz)
        try:
            for question in state.quiz.questions:
                session.submit_answer(question.id, selections[question.id])
            result = session.finish()
        except QuizSessionError as exc:
            return (
                render_template(
                    "quiz.html",
                    quiz=state.quiz,
                    token=token,
                    selections=selections,
                    error=str(exc),
                ),
                400,
            )

        session_store.save_result(token, result)
        return redirect(url_for("result_view", token=token))

    @app.get("/result/<token>")
    def result_view(token: str) -> str | Response:
        state = session_store.get(token)
        if state is None:
            flash(
                "That quiz expired or could not be found. Generate a new quiz.", "error"
            )
            return redirect(url_for("index"))
        if state.result is None:
            return redirect(url_for("quiz_view", token=token))

        percentage = state.result.score / state.result.total * 100
        wrong_ids = set(state.result.wrong_question_ids)
        return render_template(
            "result.html",
            quiz=state.quiz,
            result=state.result,
            percentage=percentage,
            wrong_ids=wrong_ids,
            token=token,
        )

    @app.get("/result/<token>/review.md")
    def download_review(token: str) -> Response:
        state = session_store.get(token)
        if state is None or state.result is None:
            flash("Complete the quiz before downloading a review.", "error")
            return redirect(url_for("index"))

        content = exporter.render_wrong_answers(state.quiz, state.result)
        return Response(
            content,
            mimetype="text/markdown",
            headers={
                "Content-Disposition": 'attachment; filename="quiz-review.md"',
            },
        )

    @app.errorhandler(413)
    def upload_too_large(error: Any) -> tuple[str, int]:
        return (
            render_template(
                "index.html",
                error="The uploaded file is too large. Choose a file smaller than 1 MB.",
                selected_mode="file",
            ),
            413,
        )

    return app


def _read_generation_source(selected_mode: str) -> tuple[str, str]:
    if selected_mode == "topic":
        topic = request.form.get("topic", "").strip()
        if not topic:
            raise WebInputError("Enter a topic before generating a quiz.")
        if len(topic) > MAX_TOPIC_CHARACTERS:
            raise WebInputError(
                f"Keep the topic under {MAX_TOPIC_CHARACTERS} characters."
            )
        return topic, "topic"

    if selected_mode == "lecture":
        lecture = request.form.get("lecture", "").strip()
        return _validated_lecture(lecture), "lecture"

    if selected_mode == "file":
        upload = request.files.get("lecture_file")
        if upload is None or not upload.filename:
            raise WebInputError("Choose a .txt lecture file.")
        if Path(upload.filename).suffix.lower() != ".txt":
            raise WebInputError("Choose a file ending in .txt.")
        raw = upload.stream.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise WebInputError("Choose a lecture file smaller than 1 MB.")
        try:
            lecture = raw.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise WebInputError("The lecture file must use UTF-8 encoding.") from exc
        return _validated_lecture(lecture), "lecture"

    raise WebInputError("Choose topic, pasted lecture, or text file input.")


def _validated_lecture(lecture: str) -> str:
    if not lecture:
        raise WebInputError("Lecture content cannot be empty.")
    if len(lecture) > MAX_LECTURE_CHARACTERS:
        raise WebInputError(
            f"Keep lecture content under {MAX_LECTURE_CHARACTERS:,} characters."
        )
    return lecture
