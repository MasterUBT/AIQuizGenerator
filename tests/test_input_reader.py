from pathlib import Path

import pytest

from ai_quiz_generator.infrastructure.input_reader import LectureInputError, read_lecture_file


def test_reads_utf8_lecture_content(tmp_path: Path) -> None:
    path = tmp_path / "lecture.TXT"
    path.write_text("  Classes and objects\nPërshëndetje!\n", encoding="utf-8")

    assert read_lecture_file(path) == "Classes and objects\nPërshëndetje!"


@pytest.mark.parametrize("content", ["", " \n\t"])
def test_rejects_empty_file(tmp_path: Path, content: str) -> None:
    path = tmp_path / "lecture.txt"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(LectureInputError, match="empty"):
        read_lecture_file(path)


def test_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(LectureInputError, match="File not found"):
        read_lecture_file(tmp_path / "missing.txt")


def test_rejects_non_text_extension(tmp_path: Path) -> None:
    with pytest.raises(LectureInputError, match=r"Choose a \.txt"):
        read_lecture_file(tmp_path / "lecture.pdf")


def test_reports_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "lecture.txt"
    path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(LectureInputError, match="UTF-8"):
        read_lecture_file(path)


def test_reports_unreadable_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*args: object, **kwargs: object) -> str:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_text", denied)

    with pytest.raises(LectureInputError, match="not readable"):
        read_lecture_file(tmp_path / "lecture.txt")


def test_reports_directory_instead_of_file(tmp_path: Path) -> None:
    directory = tmp_path / "lecture.txt"
    directory.mkdir()

    with pytest.raises(LectureInputError, match="Could not read"):
        read_lecture_file(directory)
