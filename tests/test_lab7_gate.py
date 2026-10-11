"""Lab 7: the gate's rules, offline. A judge is trusted only as calibrated; thresholds live in two places that agree;
the baseline catches a drop; CI never moves its own baseline."""

import re

import pytest

from quizforge.config import ROOT

TOTALS = {
    "lessons": 4,
    "done": 4,
    "items": 8,
    "quotes_ok": 8,
    "good": 3,
    "per_lesson": 0.0008,
    "p95": 9.3,
    "spent": 0.03,
}


@pytest.fixture
def gate():
    from evals import gate  # imported per test: where Lab 7 isn't built yet, each test fails on its own

    return gate


@pytest.fixture
def limits(gate):
    return gate.settings()[0]


@pytest.fixture
def judge(gate):
    return gate.settings()[1]


def calibration(gate, judge, **changes):
    return {**gate.record(judge, "heldout", 0.95, 0.8, 0, 1, 0.03), **changes}


def verdicts(rows):
    return {name: verdict for name, verdict, _ in rows}


def test_config_matches_criteria(limits):
    text = (ROOT / "evals/criteria.md").read_text()
    done, lessons = map(int, re.search(r"at least (\d+) of (\d+) lessons", text).groups())
    assert limits["completion"] == pytest.approx(done / lessons)
    assert re.search(r"0 items with a quote", text) and limits["quotes"] == 1.0
    assert limits["quality"] == int(re.search(r"Quality: at least (\d+)%", text)[1]) / 100
    assert limits["usd_per_lesson"] == float(re.search(r"at most \$([\d.]+) per completed lesson", text)[1])
    assert limits["p95_seconds"] == int(re.search(r"p95 at most (\d+) s", text)[1])
    assert limits["judge_agreement"] == int(re.search(r"Agreement at least (\d+)%", text)[1]) / 100
    assert limits["judge_kappa"] == float(re.search(r"kappa at least (\d+(?:\.\d+)?)", text)[1])
    assert limits["judge_false_passes"] == int(re.search(r"At most (\d+) false pass", text)[1])


def test_calibration_records_the_judge_it_measured(gate, judge):
    found = calibration(gate, judge)
    assert found["model"] == judge["model"] and found["prompt"] == judge["prompt"] and found["split"] == "heldout"
    assert found["prompt_hash"] and len(found["prompt_hash"]) == 64  # the rubric's locked hash, from prompts/judge/LOCK
    assert {"agreement", "kappa", "false_passes", "false_fails", "cost", "date"} <= found.keys()


def test_fresh_calibration_accepted(gate, judge):
    assert gate.stale(calibration(gate, judge), judge) is None


def test_stale_calibration_refused(gate, judge):
    assert "calibrate" in gate.stale(None, judge)
    assert "heldout" in gate.stale(calibration(gate, judge, split="dev"), judge)
    for key in ("model", "prompt", "prompt_hash"):
        assert "re-calibrate" in gate.stale(calibration(gate, judge, **{key: "something else"}), judge)


def test_judge_trusted_only_above_its_line(gate, judge, limits):
    assert gate.trusted(calibration(gate, judge), limits)
    lesson_7_3 = calibration(gate, judge, agreement=0.8, kappa=0.62, false_passes=2)  # the held-out run in Lesson 7.3
    assert not gate.trusted(lesson_7_3, limits)


def test_quality_is_gated_only_with_a_trusted_judge(gate, limits):
    assert verdicts(gate.checks(TOTALS, limits, judge_trusted=False))["quality"] == "below"
    assert verdicts(gate.checks(TOTALS, limits, judge_trusted=True))["quality"] == "FAIL"
    assert not gate.failed(gate.checks(TOTALS, limits, judge_trusted=False))


def test_criteria_failures_fail_the_gate(gate, limits):
    cut_off = {**TOTALS, "done": 0, "items": 0, "quotes_ok": 0, "good": 0}  # Lesson 7.4's max_tokens = 400 branch
    found = verdicts(gate.checks(cut_off, limits, judge_trusted=False))
    assert found["completion"] == "FAIL" and found["quotes"] == "FAIL"
    assert verdicts(gate.checks({**TOTALS, "p95": 31.0}, limits, False))["latency"] == "FAIL"
    assert verdicts(gate.checks({**TOTALS, "per_lesson": 0.03}, limits, False))["cost"] == "FAIL"


def test_drop_beyond_the_allowance_fails(gate):
    one_less, two_less = {**TOTALS, "done": 3}, {**TOTALS, "done": 2}
    assert verdicts(gate.drops(one_less, TOTALS, 0.25, False))["vs baseline completion"] == "PASS"
    assert verdicts(gate.drops(two_less, TOTALS, 0.25, False))["vs baseline completion"] == "FAIL"
    assert verdicts(gate.drops({**TOTALS, "good": 0}, TOTALS, 0.25, False))["vs baseline quality"] == "below"


def test_no_baseline_is_reported_not_failed(gate):
    rows = gate.drops(TOTALS, None, 0.25, False)
    assert not gate.failed(rows) and "--accept" in rows[0][2]


def test_accept_is_never_run_by_ci(gate, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(SystemExit, match="person"):
        gate.accept()


def test_summary_is_a_markdown_table(gate):
    table = gate.summary([("completion", "PASS", "4 of 4 lessons done within 2 repairs")])
    assert table.splitlines()[0] == "| check | result | detail |"
    assert "| completion | PASS | 4 of 4 lessons done within 2 repairs |" in table
