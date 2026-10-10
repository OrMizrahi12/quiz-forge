import json
from pathlib import Path

from reviewer import sdk_review
from reviewer.verdict import Verdict, schema

ROOT = Path(__file__).resolve().parent.parent


def test_schema_matches_model():
    on_disk = json.loads((ROOT / "reviewer" / "verdict.schema.json").read_text())
    assert on_disk == schema(), "regenerate it: python -m reviewer.verdict > reviewer/verdict.schema.json"


def test_the_sdk_reviewer_uses_the_same_verdict():
    assert sdk_review.Verdict is Verdict


def test_the_ci_review_sends_the_generated_schema():
    script = (ROOT / "scripts" / "ci_review.sh").read_text()
    assert "reviewer/verdict.schema.json" in script and "--json-schema" in script


def test_a_verdict_has_no_extra_fields():
    assert schema()["additionalProperties"] is False
