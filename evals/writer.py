"""The writer's upgrade evidence: qf write on the regression lessons with one model, into a copy of the bank, and each
final draft graded by code and by the calibrated judge (held constant). Run it for the pinned model, then for the
candidate; the decision rule, written before either run, compares the two.
Usage: python -m evals.writer --model claude-haiku-4-5-20251001"""

import argparse
import json
import shutil
import statistics
import tempfile
import time
import tomllib
from dataclasses import replace
from pathlib import Path

from evals.graders import grade, load
from evals.judge import SETTINGS, judge
from quizforge import sources, usage, write
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter

RATES = ("done", "code", "supported", "good")


def run(model, out=print):
    """One write job per regression lesson on this model; the totals, also saved to runs/writer-<model>.json."""
    cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
    grader = Meter(make_client(), prices, SETTINGS["model"], log=cfg.usage_log, label="judge")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(cfg.bank, Path(tmp) / "bank", ignore=shutil.ignore_patterns("pending"))
        cfg = replace(cfg, model=model, bank=Path(tmp) / "bank")
        for case in load("regression.jsonl"):
            meter, start = Meter(make_client(), prices, model, log=cfg.usage_log), time.perf_counter()
            result = write.write(meter, cfg, case["lesson"], out=lambda line: None)
            items = [
                {"lesson": case["lesson"], "item": {k: v for k, v in q.items() if k != "section"}}
                for q in result.job.questions
            ]
            row = {
                "lesson": case["lesson"],
                "stopped": result.stopped,
                "rounds": result.rounds,
                "items": len(items),
                "code": sum(all(ok for _, ok, _ in grade(item, cfg.library)) for item in items),
                "supported": sum(map(sources.supported, result.job.verdicts)),
                "good": sum(judge(grader, cfg.library, item).verdict == "good" for item in items),
                "cost": round(meter.cost, 5),
                "seconds": round(time.perf_counter() - start, 1),
                "not_supported": [line for line in result.job.verdicts if not sources.supported(line)],
            }
            rows.append(row)
            out(
                f"{row['lesson']:5} {row['stopped']:12} round {row['rounds']}  code {row['code']}/{row['items']}  "
                f"checker {row['supported']}/{row['items']}  judge good {row['good']}/{row['items']}  "
                f"${row['cost']:.4f}  {row['seconds']} s"
            )
    done = [r for r in rows if r["stopped"] == "done"]
    items = sum(r["items"] for r in rows) or 1
    totals = {
        "model": model,
        "lessons": len(rows),
        "done": len(done) / len(rows),
        **{k: sum(r[k] for r in rows) / items for k in ("code", "supported", "good")},
        "usd_per_done": sum(r["cost"] for r in rows) / max(len(done), 1),
        "p95": p95(rows),
        "judge_usd": round(grader.cost, 5),
        "rows": rows,
    }
    (ROOT / "runs" / f"writer-{model}.json").write_text(json.dumps(totals, indent=1) + "\n")
    return totals


def p95(rows):
    """The 95th percentile of the job times, within the measured range (few jobs: no extrapolation)."""
    return statistics.quantiles([r["seconds"] for r in rows], n=20, method="inclusive")[-1]


def decide(base, cand, allowance, budget):
    """The rule, written before the runs: no rate may fall more than the allowance below the baseline's, and a done
    lesson must stay within the write job's budget. Returns the reasons to hold; none means ship."""
    held = [f"{k} {cand[k]:.0%} vs {base[k]:.0%}" for k in RATES if cand[k] < base[k] - allowance]
    if cand["usd_per_done"] > budget:
        held.append(f"${cand['usd_per_done']:.4f} per done lesson is over the ${budget} job budget")
    return held


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="run the write jobs on this model")
    parser.add_argument("--against", help="compare the saved runs: this model is the baseline")
    args = parser.parse_args()
    if args.model:
        run(args.model)
    found = {p.stem.removeprefix("writer-"): json.loads(p.read_text()) for p in (ROOT / "runs").glob("writer-*.json")}
    print(f"\n{'model':27}" + "".join(f"{k:>11}" for k in RATES) + f"{'$/done':>10}{'p95 s':>8}")
    for name, t in found.items():
        print(
            f"{name:27}"
            + "".join(f"{t[k]:>11.0%}" for k in RATES)
            + f"{t['usd_per_done']:>10.4f}{p95(t['rows']):>8.1f}"
        )
    if args.against and len(found) > 1:
        cfg = load_config()
        allowance = tomllib.loads((ROOT / "config.toml").read_text())["eval"]["allowance"]
        for name, t in found.items():
            if name != args.against:
                held = decide(found[args.against], t, allowance, cfg.max_usd)
                print(
                    f"\n{name}: "
                    + (
                        "ship: within the allowance on every rate, and within budget"
                        if not held
                        else "hold: " + "; ".join(held)
                    )
                )
                for row in t["rows"]:  # the totals hide why: read every job that didn't finish
                    if row["stopped"] != "done":
                        print(f"  {row['lesson']} {row['stopped']}, the checker's last verdicts:")
                        for verdict in row["not_supported"]:
                            print(f"    {verdict[:70]}")
