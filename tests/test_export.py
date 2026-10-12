import csv
import json
from dataclasses import replace

import pytest

from quizforge import cli, export
from quizforge.config import load_config
from quizforge.security import integrity

BASE = load_config()

TRICKY = 'Which is best, "fast" or\n"cheap", for 10,000 emails?'


def question(scenario="A scenario?", answer="B", **extra):
    return {
        "scenario": scenario,
        "a": "Option A",
        "b": "Option B",
        "c": "Option C",
        "d": "Option D",
        "answer": answer,
        "why": "Because the lesson says so.",
        "quote": "A sentence from the lesson.",
        "section": "L1.3#the-rule",
        "verdict": "supported",
        "model": "claude-haiku-4-5-20251001",
        "prompt": "v4",
        "approved": "2026-10-09T15:15:00+00:00",
        **extra,
    }


def approve(tmp_path, lesson, questions, seal=True):
    folder = tmp_path / "approved"
    folder.mkdir(exist_ok=True)
    (folder / f"{lesson}.json").write_text(json.dumps({"lesson": lesson, "questions": questions}))
    if seal:
        integrity.seal(folder)
    return folder


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_csv_has_the_header_and_one_row_per_question(tmp_path):
    approve(tmp_path, "L1.1", [question("First?"), question("Second?")])
    approve(tmp_path, "L1.3", [question("Third?")])
    out = tmp_path / "exports"
    assert export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out) == 0
    rows = read_csv(out / "approved.csv")
    assert rows[0] == list(export.CSV_COLUMNS)
    assert [r[0] for r in rows[1:]] == ["L1.1", "L1.1", "L1.3"]
    assert [r[1] for r in rows[1:]] == ["First?", "Second?", "Third?"]


def test_a_stem_with_a_comma_a_quote_and_a_newline_stays_one_cell(tmp_path):
    approve(tmp_path, "L1.3", [question(TRICKY)])
    out = tmp_path / "exports"
    export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out)
    rows = read_csv(out / "approved.csv")
    assert len(rows) == 2
    assert rows[1][export.CSV_COLUMNS.index("scenario")] == TRICKY


def test_the_columns_come_from_one_constant(tmp_path, monkeypatch):
    approve(tmp_path, "L1.3", [question()])
    monkeypatch.setattr(export, "CSV_COLUMNS", ("lesson", "answer", "quote"))
    out = tmp_path / "exports"
    export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out)
    assert read_csv(out / "approved.csv") == [
        ["lesson", "answer", "quote"],
        ["L1.3", "B", "A sentence from the lesson."],
    ]


def test_the_default_columns_are_the_ones_in_the_issue():
    assert export.CSV_COLUMNS == ("lesson", "scenario", "a", "b", "c", "d", "answer", "why", "quote")


def test_csv_leaves_out_the_review_bookkeeping(tmp_path):
    approve(tmp_path, "L1.3", [question()])
    out = tmp_path / "exports"
    export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out)
    text = (out / "approved.csv").read_text()
    for left_out in ("section", "verdict", "claude-haiku", "2026-10-09"):
        assert left_out not in text


def test_markdown_sheet_lists_each_question_in_order(tmp_path):
    approve(tmp_path, "L1.1", [question("First?", "A")])
    approve(tmp_path, "L1.3", [question("Second?", "C")])
    out = tmp_path / "exports"
    assert export.run(replace(BASE, bank=tmp_path), "md", out_dir=out) == 0
    text = (out / "approved.md").read_text()
    positions = [text.index(s) for s in ("L1.1", "First?", "L1.3", "Second?")]
    assert positions == sorted(positions)
    for s in (
        "Option A",
        "Option B",
        "Option C",
        "Option D",
        "Because the lesson says so.",
        "A sentence from the lesson.",
    ):
        assert s in text
    assert "Answer: A" in text and "Answer: C" in text


def test_a_changed_file_stops_the_export(tmp_path, capsys):
    folder = approve(tmp_path, "L1.3", [question()])
    (folder / "L1.3.json").write_text(json.dumps({"lesson": "L1.3", "questions": [question("Edited?")]}))
    out = tmp_path / "exports"
    assert export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out) == 1
    assert "changed after approval" in capsys.readouterr().out
    assert not out.exists()


def test_an_unsealed_bank_stops_the_export(tmp_path):
    approve(tmp_path, "L1.3", [question()], seal=False)
    out = tmp_path / "exports"
    assert export.run(replace(BASE, bank=tmp_path), "md", out_dir=out) == 1
    assert not out.exists()


def test_an_empty_bank_writes_nothing(tmp_path, capsys):
    (tmp_path / "approved").mkdir()
    integrity.seal(tmp_path / "approved")
    out = tmp_path / "exports"
    assert export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out) == 1
    assert "nothing approved yet" in capsys.readouterr().out
    assert not out.exists()


def test_run_creates_the_output_folder_and_reports_the_path(tmp_path, capsys):
    approve(tmp_path, "L1.3", [question(), question("Again?")])
    out = tmp_path / "deep" / "exports"
    export.run(replace(BASE, bank=tmp_path), "csv", out_dir=out)
    printed = capsys.readouterr().out
    assert str(out / "approved.csv") in printed and "2" in printed


def test_the_export_command_passes_the_format_on(monkeypatch):
    seen = []
    monkeypatch.setattr(export, "run", lambda cfg, fmt, **kw: seen.append(fmt) or 0)
    assert cli.main(["export", "--format", "md"]) == 0
    assert seen == ["md"]


def test_the_export_command_rejects_other_formats(capsys):
    with pytest.raises(SystemExit) as stop:
        cli.main(["export", "--format", "xlsx"])
    assert stop.value.code == 2
