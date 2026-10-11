"""Export approved questions: a CSV, one row per question, or a Markdown review sheet. Reads bank/approved/, writes runs/exports/."""

import csv
import io
import json

COLUMNS = ("lesson", "scenario", "a", "b", "c", "d", "answer", "why", "quote")  # mirrors the platform import template


def approved(cfg):
    """Every approved question as (lesson, question), sorted by lesson then question text, so exports of the same bank diff cleanly."""
    found = []
    for path in (cfg.bank / "approved").glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        found += [(item.get("lesson", path.stem), q) for q in item["questions"]]
    return sorted(found, key=lambda row: (row[0], row[1]["scenario"]))


def to_csv(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for lesson, q in rows:
        writer.writerow({"lesson": lesson, **q})
    return out.getvalue()


def to_md(rows):
    lines = ["# Approved items", ""]
    last, n = None, 0
    for lesson, q in rows:
        if lesson != last:
            lines += [f"## {lesson}", ""]
            last, n = lesson, 0
        n += 1
        lines += [f"### Question {n}", "", q["scenario"], ""]
        lines += [f"- {key.upper()}. {q[key]}" for key in "abcd"]
        lines += ["", f"**Answer:** {q['answer']}", "", f"**Why:** {q['why']}", ""]
        lines += [f"> {line}" for line in q["quote"].splitlines()] + [""]
    return "\n".join(lines)


def export_approved(cfg, fmt, out_dir=None):
    """Write approved.csv or approved.md into out_dir (default runs/exports/); (path, question count), or None if nothing is approved."""
    rows = approved(cfg)
    if not rows:
        return None
    out_dir = out_dir or cfg.bank.parent / "runs" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"approved.{fmt}"
    path.write_text(to_csv(rows) if fmt == "csv" else to_md(rows), encoding="utf-8", newline="")
    return path, len(rows)
