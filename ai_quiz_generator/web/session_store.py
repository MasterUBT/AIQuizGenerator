"""Short-lived in-memory storage for local browser quiz sessions."""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult


@dataclass(slots=True)
class WebQuizState:
    quiz: Quiz
    created_at: float
    result: QuizResult | None = None


class QuizSessionStore:
    """Store generated quizzes without exposing answers in browser cookies."""

    def __init__(self, ttl_seconds: float = 30 * 60) -> None:
        self._ttl_seconds = ttl_seconds
        self._states: dict[str, WebQuizState] = {}
        self._lock = threading.Lock()

    def create(self, quiz: Quiz) -> str:
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._remove_expired()
            self._states[token] = WebQuizState(quiz=quiz, created_at=time.monotonic())
        return token

    def get(self, token: str) -> WebQuizState | None:
        with self._lock:
            self._remove_expired()
            return self._states.get(token)

    def save_result(self, token: str, result: QuizResult) -> bool:
        with self._lock:
            self._remove_expired()
            state = self._states.get(token)
            if state is None:
                return False
            state.result = result
            return True

    def _remove_expired(self) -> None:
        now = time.monotonic()
        expired = [
            token
            for token, state in self._states.items()
            if now - state.created_at >= self._ttl_seconds
        ]
        for token in expired:
            self._states.pop(token, None)
