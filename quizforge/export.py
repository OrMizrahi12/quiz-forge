"""Export the approved bank: a CSV, one row per question, or a Markdown review sheet, into runs/exports/.
Reads bank/approved/ only, and only if it still matches the seal (security/integrity.py).
Usage: python -m quizforge export --format csv|md"""

import csv
import json

from quizforge.config import ROOT
from quizforge.security import integrity

# The platform's import template may change: the CSV header and every row are built from this.
CSV_COLUMNS = ("lesson", "scenario", "a", "b", "c", "d", "answer", "why", "quote")

EXPORT_DIR = ROOT / "runs" / "exports"
FILES = {"csv": "approved.csv", "md": "approved.md"}


def load_approved(folder):
    """(lesson, question) for every approved question, sorted by lesson then scenario so exports diff cleanly."""
    items = []
    for path in folder.glob("*.json"):
        data = json.loads(path.read_text())
        items += [(data.get("lesson", path.stem), q) for q in data["questions"]]
    return sorted(items, key=lambda item: (item[0], item[1]["scenario"]))


def to_csv(items, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(CSV_COLUMNS)
        for lesson, q in items:
            out.writerow([lesson if name == "lesson" else q[name] for name in CSV_COLUMNS])


def to_markdown(items, path):
    lines = [
        "# Approved practice questions",
        "",
        "_Questions are written with AI and approved by a person._",
    ]
    current, number = None, 0
    for lesson, q in items:
        if lesson != current:
            current, number = lesson, 0
            lines += ["", f"## {lesson}"]
        number += 1
        lines += ["", f"### {number}. {q['scenario']}", ""]
        lines += [f"- {letter}. {q[letter.lower()]}" for letter in "ABCD"]
        lines += ["", f"**Answer: {q['answer']}.** {q['why']}", "", f"> {q['quote']}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(cfg, fmt, out_dir=EXPORT_DIR):
    folder = cfg.bank / "approved"
    if not any(folder.glob("*.json")):  # before verify: an empty bank's seal is a blank line verify can't read
        print("nothing approved yet")
        return 1
    problems = integrity.verify(folder)
    if problems:
        print("\n".join(problems))
        print("not exporting: the approved bank does not match its seal")
        return 1
    items = load_approved(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / FILES[fmt]
    (to_csv if fmt == "csv" else to_markdown)(items, path)
    print(f"{len(items)} question(s) -> {path}")
    return 0
