"""Terminal menus and quiz flow, independent of the selected AI provider."""

from collections.abc import Callable

from ai_quiz_generator.domain.question import Question
from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult
from ai_quiz_generator.infrastructure.input_reader import (
    LectureInputError,
    read_lecture_file,
)
from ai_quiz_generator.infrastructure.quiz_exporter import QuizExporter, QuizExportError
from ai_quiz_generator.services.quiz_generator import (
    InvalidGenerationRequestError,
    QuizGenerationError,
    QuizGenerator,
)
from ai_quiz_generator.services.quiz_session import InvalidChoiceError, QuizSession


class TerminalUI:
    """Collect user input and delegate generation, grading, and export."""

    def __init__(
        self,
        generator: QuizGenerator,
        exporter: QuizExporter,
        *,
        read: Callable[[str], str] | None = None,
        write: Callable[[str], None] | None = None,
    ) -> None:
        self._generator = generator
        self._exporter = exporter
        self._read = read if read is not None else input
        self._write = write if write is not None else print

    def run(self) -> None:
        """Run until exit, end of input, or Ctrl+C."""
        self._write("AI Quiz Generator")
        try:
            self._menu_loop()
        except EOFError:
            self._write("\nInput closed. Goodbye!")
        except KeyboardInterrupt:
            self._write("\nQuiz cancelled. Goodbye!")

    def _menu_loop(self) -> None:
        while True:
            self._write("\n1. Topic\n2. Paste lecture\n3. Load .txt file\n4. Exit")
            choice = self._read("Choose 1–4: ").strip()
            if choice == "4":
                self._write("Goodbye!")
                return
            if choice not in {"1", "2", "3"}:
                self._write("Please choose 1, 2, 3, or 4.")
                continue
            try:
                source, mode = self._read_source(choice)
                if source is None:
                    self._write("Lecture entry cancelled. Returning to the menu.")
                    continue
                self._write("Preparing your quiz…")
                quiz = self._generator.generate(source, mode)
            except (LectureInputError, InvalidGenerationRequestError, QuizGenerationError) as exc:
                self._write(f"Could not start quiz: {exc}")
                continue
            self._play_quiz(quiz)

    def _read_source(self, choice: str) -> tuple[str | None, str]:
        if choice == "1":
            return self._read_required("Topic: "), "topic"
        if choice == "2":
            return self._read_lecture(), "lecture"
        path = self._read_required("Lecture .txt path: ")
        return read_lecture_file(path), "lecture"

    def _read_required(self, prompt: str) -> str:
        while True:
            text = self._read(prompt).strip()
            if text:
                return text
            self._write("Input cannot be empty. Please try again.")

    def _read_lecture(self) -> str | None:
        while True:
            self._write("Paste your lecture. Enter END on its own line to finish.")
            self._write("Type /cancel on its own line to return to the menu.")
            lines = []
            while True:
                line = self._read("")
                if line.strip().lower() == "/cancel":
                    return None
                if line == "END":
                    break
                lines.append(line)
            content = "\n".join(lines).strip()
            if content:
                return content
            self._write("Lecture cannot be empty. Please try again.")

    def _play_quiz(self, quiz: Quiz) -> None:
        self._write(f"\nQuiz: {quiz.topic}")
        session = QuizSession(quiz)
        for number, question in enumerate(quiz.questions, start=1):
            self._write(f"\nQuestion {number}/{len(quiz.questions)}: {question.text}")
            for letter in "ABCD":
                self._write(f"  {letter}. {question.options[letter]}")
            if not self._collect_answer(session, question):
                self._write("Quiz cancelled. Returning to the menu.")
                return

        result = session.finish()
        percentage = result.score / result.total * 100
        self._write(f"\nFinal score: {result.score}/{result.total} ({percentage:.0f}%)")
        self._offer_export(quiz, result)

    def _collect_answer(self, session: QuizSession, question: Question) -> bool:
        while True:
            choice = self._read("Your answer (A–D, /cancel to return to menu): ")
            if choice.strip().lower() == "/cancel":
                return False
            try:
                session.submit_answer(question.id, choice)
            except InvalidChoiceError:
                self._write("Please enter A, B, C, or D.")
            else:
                return True

    def _offer_export(self, quiz: Quiz, result: QuizResult) -> None:
        while True:
            answer = self._read("Save incorrect answers? [y/N]: ").strip().lower()
            if answer in {"", "n", "no"}:
                return
            if answer in {"y", "yes"}:
                break
            self._write("Please answer yes or no.")

        while True:
            path = self._read("Export path (.md or .txt; Enter to cancel): ").strip()
            if not path:
                self._write("Export cancelled.")
                return
            try:
                self._exporter.export_wrong_answers(quiz, result, path)
            except QuizExportError as exc:
                self._write(str(exc))
            else:
                self._write(f"Review saved to {path}")
                return
