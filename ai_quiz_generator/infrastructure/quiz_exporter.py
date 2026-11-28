"""Export a completed quiz's incorrect answers as readable Markdown."""

from pathlib import Path

from ai_quiz_generator.domain.quiz import Quiz
from ai_quiz_generator.domain.quiz_result import QuizResult


class QuizExportError(ValueError):
    """A quiz review could not be saved."""


class QuizExporter:
    """Write quiz reviews without overwriting existing files."""

    def export_wrong_answers(self, quiz: Quiz, result: QuizResult, path: str) -> None:
        output_path = Path(path).expanduser()
        if output_path.suffix.lower() not in {".md", ".txt"}:
            raise QuizExportError("Choose an export path ending in .md or .txt.")

        content = self.render_wrong_answers(quiz, result)
        try:
            with output_path.open("x", encoding="utf-8") as output:
                output.write(content)
        except FileExistsError as exc:
            raise QuizExportError(
                "That file already exists. Choose another path."
            ) from exc
        except (OSError, UnicodeError, ValueError) as exc:
            raise QuizExportError(
                f"Could not write review to {output_path}. Check the folder and permissions."
            ) from exc

    @staticmethod
    def render_wrong_answers(quiz: Quiz, result: QuizResult) -> str:
        """Return the same review content used by file exports."""
        question_ids = {question.id for question in quiz.questions}
        wrong_ids = set(result.wrong_question_ids)
        if (
            result.total != len(quiz.questions)
            or set(result.answers) != question_ids
            or not wrong_ids.issubset(question_ids)
        ):
            raise QuizExportError("The result does not match this quiz.")

        lines = [
            f"# Quiz review: {quiz.topic}",
            "",
            f"Score: {result.score}/{result.total}",
            "",
        ]
        if not wrong_ids:
            lines.append("No incorrect answers. Well done!")

        for question in quiz.questions:
            if question.id not in wrong_ids:
                continue
            selected = result.answers[question.id]
            if selected not in question.options:
                raise QuizExportError("The result contains an invalid answer.")
            correct = question.correct_answer
            lines.extend(
                [
                    f"## Question {question.id}",
                    "",
                    question.text,
                    "",
                    f"**Your answer:** {selected} — {question.options[selected]}",
                    f"**Correct answer:** {correct} — {question.options[correct]}",
                    "",
                    f"**Explanation:** {question.explanation}",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"
