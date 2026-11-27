"""Read lecture content from UTF-8 text files."""

from pathlib import Path


class LectureInputError(ValueError):
    """A lecture file could not provide usable text."""


def read_lecture_file(path: str | Path) -> str:
    """Read a nonempty .txt file, translating file errors for the terminal."""
    file_path = Path(path).expanduser()
    if file_path.suffix.lower() != ".txt":
        raise LectureInputError("Choose a .txt file.")

    try:
        content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LectureInputError(f"File not found: {file_path}") from exc
    except PermissionError as exc:
        raise LectureInputError(f"File is not readable: {file_path}") from exc
    except UnicodeError as exc:
        raise LectureInputError("The lecture file must use UTF-8 encoding.") from exc
    except (OSError, ValueError) as exc:
        raise LectureInputError(f"Could not read lecture file: {file_path}") from exc

    if not content.strip():
        raise LectureInputError("The lecture file is empty.")
    return content.strip()
