"""Lab 9, FR-7: each exported row carries its lesson's domain from the blueprint. Files only, no API calls."""

import csv
import json
from dataclasses import replace

from quizforge import export
from quizforge.config import load_config
from quizforge.security import integrity

BASE = load_config()
BLUEPRINT = '[[domain]]\nname = "Breads"\nweight = 100\nlessons = ["B1.1"]\n'


def question(n, scenario=None):
    return {
        "scenario": scenario or f"Scenario {n}. What now?",
        **{key: f"{key} {n}" for key in "abcd"},
        "answer": "B",
        "why": f"Because {n}.",
        "quote": f"Quote {n}.",
    }


def deployment(tmp_path, blueprint=BLUEPRINT):
    """A deployment folder: bank/approved (sealed, as qf review leaves it), one pending item, and maybe a blueprint."""
    for state, lesson, n in (("approved", "B1.1", 1), ("approved", "B1.2", 2), ("pending", "B1.1", 3)):
        path = tmp_path / "bank" / state / f"{lesson}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        stem = 'She said "rise"\nand waited. Why?' if n == 1 else None
        path.write_text(json.dumps({"lesson": lesson, "questions": [question(n, stem)]}))
    integrity.seal(tmp_path / "bank" / "approved")
    if blueprint:
        (tmp_path / "blueprint.toml").write_text(blueprint)
    return replace(BASE, bank=tmp_path / "bank")


def exported(tmp_path, fmt="csv", **kw):
    out = tmp_path / "out"
    assert export.run(deployment(tmp_path, **kw), fmt, out_dir=out) == 0
    return out / export.FILES[fmt]


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_the_domain_column_comes_from_the_blueprint(tmp_path):
    found = rows(exported(tmp_path))
    assert export.CSV_COLUMNS[:2] == ("lesson", "domain")
    assert {row["lesson"]: row["domain"] for row in found} == {"B1.1": "Breads", "B1.2": ""}


def test_only_approved_items_and_text_survives_a_round_trip(tmp_path):
    found = rows(exported(tmp_path))
    assert len(found) == 2 and not any("Scenario 3" in row["scenario"] for row in found)
    assert found[0]["scenario"] == 'She said "rise"\nand waited. Why?'


def test_without_a_blueprint_the_column_is_empty(tmp_path):
    assert [row["domain"] for row in rows(exported(tmp_path, blueprint=None))] == ["", ""]


def test_the_review_sheet_names_the_domain(tmp_path):
    assert "Domain: Breads" in exported(tmp_path, "md").read_text()
