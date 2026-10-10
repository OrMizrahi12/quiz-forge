import asyncio

import pytest

from reviewer import sdk_review
from reviewer.sdk_review import ROOT, Verdict, stay_in_scope


@pytest.fixture(autouse=True)
def log_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(sdk_review, "RUNS", tmp_path)  # the hook's log goes to a temp folder, not runs/reviews


def decide(tool, **args):
    return asyncio.run(stay_in_scope({"tool_name": tool, "tool_input": args}, "t1", None))


def test_reads_in_the_bank_are_allowed():
    assert decide("Read", file_path=str(ROOT / "bank" / "pending" / "x.json")) == {}


def test_reads_outside_the_scope_are_denied():
    out = decide("Read", file_path=str(ROOT / "config.toml"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_a_verdict_must_be_pass_or_fail():
    Verdict.model_validate({"item_id": "L1.3", "verdict": "fail", "reasons": ["key names a wrong option"], "rule": "2"})
    with pytest.raises(ValueError):
        Verdict.model_validate({"item_id": "L1.3", "verdict": "maybe", "reasons": [], "rule": None})
