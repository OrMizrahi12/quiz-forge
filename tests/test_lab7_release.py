"""Lab 7: the pipeline and the release document. The gate runs only after the offline tests, only on relevant
paths, with read-only permissions, a spend cap and superseded runs cancelled; merging and accepting stay human."""

import re

from quizforge.config import ROOT

WORKFLOW = (ROOT / ".github/workflows/evals.yml").read_text()


def test_the_gate_runs_through_qf_eval_with_a_cap():
    assert re.search(r"python -m quizforge eval --gate --max-usd [\d.]+", WORKFLOW)
    assert "evals.run" not in WORKFLOW


def test_unit_first_then_the_gate():
    assert re.search(r"gate:\n(\s+.*\n)*?\s+needs: unit", WORKFLOW)
    assert "python -m pytest -q" in WORKFLOW and "timeout-minutes:" in WORKFLOW


def test_bounded_and_read_only():
    assert re.search(r"permissions:\n\s+contents: read", WORKFLOW)
    assert "cancel-in-progress: true" in WORKFLOW
    for path in ("prompts/**", "quizforge/**", "evals/**", "config.toml"):
        assert path in WORKFLOW


def test_release_doc_names_what_only_a_person_decides():
    doc = (ROOT / "docs/release.md").read_text()
    assert "--accept" in doc and "person" in doc and "Merging" in doc
    assert "--calibrate --split heldout" in doc
