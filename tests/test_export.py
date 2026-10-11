import csv
import json
from dataclasses import replace

import pytest

from quizforge import cli, export
from quizforge.config import load_config

BASE = load_config()
STEM = 'Ana said, "stop"\nthen left. What now?'


def question(n, **change):
    q = {
        "scenario": f"Scenario {n}. What now?",
        "a": "one",
        "b": "two",
        "c": "three",
        "d": "four",
        "answer": "B",
        "why": f"Because {n}.",
        "quote": f"Quote {n}.",
        "section": "L1.3#idea",
        "verdict": "supported",
        "model": "m",
        "prompt": "v4",
        "approved": "2026-01-01T00:00:00+00:00",
    }
    return {**q, **change}


def put(tmp_path, folder, lesson, questions):
    path = tmp_path / "bank" / folder / f"{lesson}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"lesson": lesson, "questions": questions}))
    return path


def cfg_for(tmp_path):
    return replace(BASE, bank=tmp_path / "bank")


def rows_of(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_columns_pinned():
    assert export.COLUMNS == ("lesson", "scenario", "a", "b", "c", "d", "answer", "why", "quote")


def test_csv_header_and_rows_across_lessons(tmp_path):
    put(tmp_path, "approved", "L2.1", [question(3)])
    put(tmp_path, "approved", "L1.3", [question(1), question(2)])
    path, n = export.export_approved(cfg_for(tmp_path), "csv", tmp_path / "out")
    assert n == 3
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(export.COLUMNS)
    rows = rows_of(path)
    assert [(r["lesson"], r["scenario"]) for r in rows] == [
        ("L1.3", "Scenario 1. What now?"),
        ("L1.3", "Scenario 2. What now?"),
        ("L2.1", "Scenario 3. What now?"),
    ]
    assert set(rows[0]) == set(export.COLUMNS)  # section, verdict, model... are not exported


@pytest.mark.parametrize("fmt", ["csv", "md"])
def test_rows_sorted_by_lesson_then_question(tmp_path, fmt):
    put(tmp_path, "approved", "L2.1", [question(1, scenario="Beta?"), question(2, scenario="Alpha?")])
    put(tmp_path, "approved", "L1.3", [question(3, scenario="Zulu?"), question(4, scenario="Mike?")])
    path, _ = export.export_approved(cfg_for(tmp_path), fmt, tmp_path / "out")
    expected = ["Mike?", "Zulu?", "Alpha?", "Beta?"]
    if fmt == "csv":
        assert [r["scenario"] for r in rows_of(path)] == expected
    else:
        text = path.read_text(encoding="utf-8")
        positions = [text.index(s) for s in expected]
        assert positions == sorted(positions)


def test_csv_survives_comma_quote_and_newline(tmp_path):
    put(tmp_path, "approved", "L1.3", [question(1, scenario=STEM, why=STEM), question(2)])
    path, n = export.export_approved(cfg_for(tmp_path), "csv", tmp_path / "out")
    rows = rows_of(path)
    assert n == len(rows) == 2
    assert rows[0]["scenario"] == STEM
    assert rows[0]["why"] == STEM
    assert rows[1]["scenario"] == "Scenario 2. What now?"


def test_markdown_sheet(tmp_path):
    put(tmp_path, "approved", "L1.3", [question(1), question(2)])
    put(tmp_path, "approved", "L2.1", [question(3)])
    path, n = export.export_approved(cfg_for(tmp_path), "md", tmp_path / "out")
    text = path.read_text(encoding="utf-8")
    assert n == 3 and path.name == "approved.md"
    for needle in ("## L1.3", "## L2.1", "### Question 1", "### Question 2", "Scenario 3. What now?"):
        assert needle in text
    for needle in ("A. one", "B. two", "C. three", "D. four", "**Answer:** B", "**Why:** Because 1.", "> Quote 1."):
        assert needle in text


def test_only_approved_is_read(tmp_path):
    put(tmp_path, "approved", "L1.3", [question(1)])
    put(tmp_path, "pending", "L1.4", [question(7, scenario="PENDING?")])
    put(tmp_path, "declined", "L1.5", [question(8, scenario="DECLINED?")])
    path, n = export.export_approved(cfg_for(tmp_path), "csv", tmp_path / "out")
    assert n == 1
    assert "PENDING" not in path.read_text() and "DECLINED" not in path.read_text()


@pytest.mark.parametrize("fmt", ["csv", "md"])
def test_nothing_approved_writes_nothing(tmp_path, fmt):
    put(tmp_path, "pending", "L1.3", [question(1)])
    assert export.export_approved(cfg_for(tmp_path), fmt, tmp_path / "out") is None
    assert not (tmp_path / "out").exists()


def test_output_name_directory_and_overwrite(tmp_path):
    put(tmp_path, "approved", "L1.3", [question(1)])
    out = tmp_path / "deep" / "out"
    path, _ = export.export_approved(cfg_for(tmp_path), "csv", out)
    assert path == out / "approved.csv"
    put(tmp_path, "approved", "L1.3", [question(1), question(2)])
    path, n = export.export_approved(cfg_for(tmp_path), "csv", out)
    assert n == 2 and len(rows_of(path)) == 2


def test_default_directory_is_runs_exports(tmp_path):
    put(tmp_path, "approved", "L1.3", [question(1)])
    path, _ = export.export_approved(cfg_for(tmp_path), "csv")
    assert path == tmp_path / "runs" / "exports" / "approved.csv"


def test_export_leaves_approved_untouched(tmp_path):
    files = [put(tmp_path, "approved", "L1.3", [question(1)]), put(tmp_path, "approved", "L2.1", [question(2)])]
    before = {p: p.read_bytes() for p in files}
    export.export_approved(cfg_for(tmp_path), "csv", tmp_path / "out")
    export.export_approved(cfg_for(tmp_path), "md", tmp_path / "out")
    assert {p: p.read_bytes() for p in files} == before
    assert sorted(p.name for p in (tmp_path / "bank" / "approved").iterdir()) == ["L1.3.json", "L2.1.json"]


def test_cli_rejects_unknown_format():
    with pytest.raises(SystemExit):
        cli.main(["export", "--format", "xml"])


def test_cli_writes_and_reports(tmp_path, monkeypatch, capsys):
    put(tmp_path, "approved", "L1.3", [question(1)])
    monkeypatch.setattr(cli, "load_config", lambda: cfg_for(tmp_path))
    assert cli.main(["export", "--format", "csv"]) == 0
    assert "1 question(s)" in capsys.readouterr().out
    assert len(rows_of(tmp_path / "runs" / "exports" / "approved.csv")) == 1


def test_cli_with_nothing_approved_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_config", lambda: cfg_for(tmp_path))
    assert cli.main(["export", "--format", "md"]) == 1
    assert "no approved questions" in capsys.readouterr().out
    assert not (tmp_path / "runs").exists()
