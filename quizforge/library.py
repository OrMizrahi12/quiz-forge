import json
from pathlib import Path


def lesson_ids(library: Path) -> list[str]:
    manifest = json.loads((library / "MANIFEST.json").read_text())
    return [row["lesson"] for row in manifest["lessons"]]


def load_lesson(library: Path, lesson: str) -> str:
    known = lesson_ids(library)
    if lesson not in known:
        raise ValueError(f"unknown lesson {lesson!r}; the library has {', '.join(known)}")
    return (library / f"{lesson}.md").read_text()
