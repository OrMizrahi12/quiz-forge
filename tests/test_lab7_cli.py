"""Lab 7: qf eval and qf report, end to end through the CLI, with no request sent (the gate is checked with a fake
eval run)."""

import json

import pytest

from quizforge import cli

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
def gate(monkeypatch, tmp_path):
    """evals.gate with its files in a temporary folder; imported per test, so where Lab 7 isn't built yet each test
    fails on its own."""
    from evals import gate

    for name in ("CALIBRATION", "BASELINE", "LAST_RUN"):
        monkeypatch.setattr(gate, name, tmp_path / f"{name.lower()}.json")
    return gate


def calibrated(gate):
    _, judge = gate.settings()
    gate.CALIBRATION.write_text(json.dumps(gate.record(judge, "heldout", 0.8, 0.62, 2, 0, 0.03)))


def fake_eval(monkeypatch, totals, seen=None):
    from evals import run

    def evaluate(cfg, prices, cases, max_usd, out=print):
        if seen is not None:
            seen.append(max_usd)
        return dict(totals)

    monkeypatch.setattr(run, "evaluate", evaluate)


def fake_calibration(monkeypatch, **row):
    from evals import calibrate

    found = {"agreement": 0.8, "kappa": 0.62, "false_passes": 2, "false_fails": 0, "cost": 0.0347, **row}
    monkeypatch.setattr(calibrate, "calibrate", lambda cfg, split, *a, **k: dict(found))


def test_gate_refuses_a_stale_judge_before_any_request(gate, monkeypatch, capsys):
    from evals import run

    monkeypatch.setattr(run, "evaluate", lambda *a, **k: pytest.fail("the gate sent a request with no calibration"))
    assert cli.main(["eval", "--gate"]) == 1
    assert "refused before any request" in capsys.readouterr().out


def test_gate_passes_and_records_its_run(gate, monkeypatch, capsys):
    calibrated(gate)
    fake_eval(monkeypatch, TOTALS)
    assert cli.main(["eval", "--gate"]) == 0
    out = capsys.readouterr().out
    assert "quality is reported, not gated" in out and "gate: pass" in out
    assert json.loads(gate.LAST_RUN.read_text())["passed"] is True


def test_gate_fails_on_the_criteria(gate, monkeypatch):
    calibrated(gate)
    fake_eval(monkeypatch, {**TOTALS, "done": 0, "items": 0, "quotes_ok": 0, "good": 0})
    assert cli.main(["eval", "--gate"]) == 1


def test_gate_spend_cap_from_config(gate, monkeypatch):
    calibrated(gate)
    caps = []
    fake_eval(monkeypatch, TOTALS, caps)
    cli.main(["eval", "--gate"])
    cli.main(["eval", "--gate", "--max-usd", "0.05"])
    assert caps == [gate.settings()[0]["max_usd"], 0.05]


def test_accept_then_a_drop_fails(gate, monkeypatch):
    calibrated(gate)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    fake_eval(monkeypatch, TOTALS)
    cli.main(["eval", "--gate"])
    assert cli.main(["eval", "--accept"]) == 0 and json.loads(gate.BASELINE.read_text())["done"] == 4
    fake_eval(monkeypatch, {**TOTALS, "done": 2})
    assert cli.main(["eval", "--gate"]) == 1


def test_calibrate_writes_the_record_and_holds_the_line(gate, monkeypatch):
    fake_calibration(monkeypatch)
    assert cli.main(["eval", "--calibrate", "--split", "heldout"]) == 1  # below 90% / 0.7: recorded, and it says so
    found = json.loads(gate.CALIBRATION.read_text())
    assert found["split"] == "heldout" and found["agreement"] == 0.8 and found["prompt_hash"]
    fake_calibration(monkeypatch, agreement=0.95, kappa=0.8, false_passes=0)
    assert cli.main(["eval", "--calibrate", "--split", "heldout"]) == 0


def test_calibrating_on_dev_records_nothing(gate, monkeypatch):
    fake_calibration(monkeypatch, agreement=1.0, kappa=1.0, false_passes=0)
    assert cli.main(["eval", "--calibrate", "--split", "dev"]) == 0
    assert not gate.CALIBRATION.exists()


def row(minute, label, model, cost, seconds, cache_write=0, cache_read=0):
    return {
        "time": f"2026-10-11T10:{minute:02d}:00+00:00",
        "label": label,
        "model": model,
        "input": 900,
        "cache_write": cache_write,
        "cache_read": cache_read,
        "output": 800,
        "cost": cost,
        "seconds": seconds,
    }


ROWS = [
    row(0, "L1.3 v4 attempt 1", "claude-haiku-5-5", 0.012, 8.0, cache_write=6000),
    row(1, "L1.3 v4 attempt 2", "claude-haiku-5-5", 0.011, 35.0, cache_read=6000),  # one lesson, two attempts: $0.023
    row(2, "judge", "claude-sonnet-5-5", 0.004, 5.0),
]


@pytest.fixture
def report(tmp_path, monkeypatch):
    """quizforge.report on a fixture log, with the clock at 12:00 that day."""
    from quizforge import report

    log = tmp_path / "usage.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    monkeypatch.setattr(report, "load_config", lambda: type("Cfg", (), {"usage_log": log})())
    noon = report.datetime.fromisoformat("2026-10-11T12:00:00+00:00")
    clock = type(
        "Clock",
        (),
        {"now": staticmethod(lambda tz: noon), "fromisoformat": staticmethod(report.datetime.fromisoformat)},
    )
    monkeypatch.setattr(report, "datetime", clock)
    return report


def test_report_marks_each_breach(report, capsys):
    assert cli.main(["report", "--since", "1d"]) == 1
    out = capsys.readouterr().out.splitlines()
    generate = next(line for line in out if line.startswith("generate"))
    assert "OVER usd_per_task 0.02" in generate and "p95_seconds 30" in generate
    assert "ok" in next(line for line in out if line.startswith("judge"))
    assert cli.main(["report", "--since", "1d", "--by", "model"]) == 0  # by model: no budgets to break
    assert cli.main(["report", "--since", "1h"]) == 0  # nothing in the last hour


def test_since_takes_days_hours_and_minutes(report):
    assert report.hours("1d") == 24 and report.hours("12h") == 12 and report.hours("90m") == 1.5
    with pytest.raises(SystemExit, match="--since"):
        report.hours("yesterday")
