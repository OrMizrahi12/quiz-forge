"""The release gate for generate. Before any request it checks that the judge was calibrated in its current form
(model, rubric version, rubric hash); then it holds an eval run against the thresholds in config.toml [eval] (they
mirror evals/criteria.md) and against the last accepted baseline. Run it with: python -m quizforge eval --gate"""

import json
import os
import tomllib
from datetime import date

from quizforge.config import ROOT
from quizforge.prompts import locked

CALIBRATION = ROOT / "evals/calibration.json"
BASELINE = ROOT / "evals/baseline.json"
LAST_RUN = ROOT / "runs/last-gate.json"


def settings():
    """([eval] thresholds, [judge] model and rubric) from config.toml."""
    config = tomllib.loads((ROOT / "config.toml").read_text())
    return config["eval"], config["judge"]


def identity(judge):
    """What a calibration is valid for: the judge's model, its rubric version, and that version's locked hash."""
    return {
        "model": judge["model"],
        "prompt": judge["prompt"],
        "prompt_hash": locked(ROOT / "prompts/judge").get(judge["prompt"]),
    }


def record(judge, split, agreement, kappa, false_passes, false_fails, cost):
    """The calibration as the gate will check it, with the judge identity it was measured on."""
    return {
        **identity(judge),
        "split": split,
        "agreement": round(agreement, 3),
        "kappa": round(kappa, 3),
        "false_passes": false_passes,
        "false_fails": false_fails,
        "cost": round(cost, 5),
        "date": date.today().isoformat(),
    }


def trusted(calibration, limits):
    """Did the judge meet its own line on the held-out labels?"""
    return (
        calibration["agreement"] >= limits["judge_agreement"]
        and calibration["kappa"] >= limits["judge_kappa"]
        and calibration["false_passes"] <= limits["judge_false_passes"]
    )


def stale(calibration, judge):
    """Why the gate must not run with this judge, or None. A judge is trusted only as far as its last calibration."""
    if calibration is None:
        return "no evals/calibration.json: calibrate the judge first (python -m quizforge eval --calibrate --split heldout)"
    if calibration.get("split") != "heldout":
        return f"the judge was calibrated on {calibration.get('split')}; only heldout counts"
    now = identity(judge)
    for key in ("model", "prompt", "prompt_hash"):
        if calibration.get(key) != now[key]:
            return (
                f"the judge's {key} changed since its calibration ({calibration.get(key)} -> {now[key]}): "
                "re-calibrate the judge before it can gate"
            )
    return None


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def checks(totals, limits, judge_trusted):
    """[(name, verdict, detail)]: PASS, FAIL, or "below" for quality while the judge hasn't earned a gate."""
    lessons, items = totals["lessons"], max(totals["items"], 1)
    found = [
        (
            "completion",
            totals["done"] >= limits["completion"] * lessons,
            f"{totals['done']} of {lessons} lessons done within 2 repairs",
        ),
        (
            "quotes",
            totals["items"] > 0 and totals["quotes_ok"] >= limits["quotes"] * totals["items"],
            f"{totals['quotes_ok']} of {totals['items']} items quote their lesson word for word",
        ),
        (
            "quality",
            totals["items"] > 0 and totals["good"] >= limits["quality"] * totals["items"],
            f"{totals['good']} of {totals['items']} items judged good ({totals['good'] / items:.0%})",
        ),
        ("cost", totals["per_lesson"] <= limits["usd_per_lesson"], f"${totals['per_lesson']:.4f} per completed lesson"),
        ("latency", totals["p95"] <= limits["p95_seconds"], f"p95 {totals['p95']:.1f} s per lesson"),
    ]
    ungated = set() if judge_trusted else {"quality"}  # an uncalibrated score is reported, never gated
    return [(name, "PASS" if ok else ("below" if name in ungated else "FAIL"), detail) for name, ok, detail in found]


def rates(totals):
    items = max(totals["items"], 1)
    return {
        "completion": totals["done"] / max(totals["lessons"], 1),
        "quotes": totals["quotes_ok"] / items,
        "quality": totals["good"] / items,
    }


def drops(totals, baseline, allowance, judge_trusted):
    """[(name, verdict, detail)] for each rate that fell further below the accepted baseline than the allowance."""
    if baseline is None:
        return [("baseline", "none", "no accepted baseline yet: a person runs --accept on main after a passing run")]
    now, then, found = rates(totals), rates(baseline), []
    for name in now:
        fell = then[name] - now[name] > allowance
        verdict = "FAIL" if fell and (name != "quality" or judge_trusted) else ("below" if fell else "PASS")
        found.append((f"vs baseline {name}", verdict, f"{now[name]:.0%} now, {then[name]:.0%} accepted"))
    return found


def summary(rows):
    """The Markdown table for the job's summary page."""
    return "| check | result | detail |\n|---|---|---|\n" + "".join(f"| {n} | {v} | {d} |\n" for n, v, d in rows)


def publish(rows, out=print):
    for name, verdict, detail in rows:
        out(f"{verdict:5} {name:22} {detail}")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as page:
            page.write(summary(rows))


def failed(rows):
    return any(verdict == "FAIL" for _, verdict, _ in rows)


def accept(out=print):
    """A person's decision: the last passing gate run becomes the baseline. Never from CI."""
    if os.environ.get("GITHUB_ACTIONS"):
        raise SystemExit("--accept is a person's decision, made on main; CI never moves its own baseline")
    last = load(LAST_RUN)
    if last is None or not last["passed"]:
        raise SystemExit("no passing gate run to accept: run python -m quizforge eval --gate first")
    BASELINE.write_text(json.dumps(last["totals"], indent=1) + "\n")
    out(f"baseline accepted: {last['date']}, {rates(last['totals'])}")
