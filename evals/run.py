"""The capability eval for generate: each lesson in evals/cases.jsonl is generated, graded by code, then by the
calibrated judge, and the totals are held against config.toml [eval] (which mirrors evals/criteria.md).
Usage: python -m evals.run   (the release gate is python -m quizforge eval --gate)"""
import argparse
import statistics
import time

from evals import gate
from evals.graders import grade, load
from evals.judge import SETTINGS, judge
from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_one
from quizforge.meter import Meter


def evaluate(cfg, prices, cases, max_usd, out=print):
    """Generate, grade and judge each case; stop before the run spends more than max_usd. Returns the totals."""
    meter = Meter(make_client(), prices, SETTINGS["model"], log=cfg.usage_log, label="judge")
    done, items, good, quotes_ok, seconds, spent = [], 0, 0, 0, [], 0.0
    for case in cases:
        if spent + meter.cost >= max_usd:
            out(f"stopped: ${spent + meter.cost:.4f} spent, the cap is ${max_usd}")
            break
        start = time.perf_counter()
        result = generate_one(cfg, prices, case["lesson"], out=lambda line: None)
        seconds.append(time.perf_counter() - start)
        spent += result["cost"]
        found = [{"lesson": case["lesson"], "item": q} for q in result.get("questions", [])]
        graded = [grade(item, cfg.library) for item in found]
        passed = [item for item, checks in zip(found, graded) if all(ok for _, ok, _ in checks)]
        quotes_ok += sum(all(ok for name, ok, _ in checks if name == "rules") for checks in graded)
        judged = sum(judge(meter, cfg.library, item).verdict == "good" for item in passed)
        items, good = items + len(found), good + judged
        if result["status"] == "passed":
            done.append(result["cost"])
        out(f"{case['lesson']:5} {result['status']:8} {result['attempts']} attempt(s)  code {len(passed)}/{len(found)}"
            f"  judge good {judged}/{len(found)}  ${result['cost']:.4f}  {seconds[-1]:.1f} s")
    p95 = statistics.quantiles(seconds, n=20)[-1] if len(seconds) > 1 else (seconds or [0.0])[0]
    out(f"\njudge: {meter.requests} requests, ${meter.cost:.4f}; total ${spent + meter.cost:.4f}")
    return {"lessons": len(cases), "done": len(done), "items": items, "quotes_ok": quotes_ok, "good": good,
            "per_lesson": sum(done) / max(len(done), 1), "p95": p95, "spent": round(spent + meter.cost, 5)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="cases.jsonl")
    parser.add_argument("--max-usd", type=float, default=1.0, help="stop before the run spends more than this")
    args = parser.parse_args()
    cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
    limits, judge_settings = gate.settings()
    calibration = gate.load(gate.CALIBRATION)
    trusted = calibration is not None and gate.stale(calibration, judge_settings) is None and gate.trusted(calibration, limits)
    rows = gate.checks(evaluate(cfg, prices, load(args.cases), args.max_usd), limits, trusted)
    gate.publish(rows)
    raise SystemExit(1 if gate.failed(rows) else 0)
