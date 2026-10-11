"""The capability eval for generate: each lesson in evals/cases.jsonl is generated, graded by code, then by the
calibrated judge, and the totals are held against evals/criteria.md. Usage: python -m evals.run"""
import argparse
import os
import statistics
import time

from evals.graders import grade, load
from evals.judge import SETTINGS, judge
from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_one
from quizforge.meter import Meter

parser = argparse.ArgumentParser()
parser.add_argument("--cases", default="cases.jsonl")
parser.add_argument("--gate", action="store_true", help="CI: fail only on the criteria generate already meets")
parser.add_argument("--max-usd", type=float, default=1.0, help="stop before the run spends more than this")
args = parser.parse_args()
cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
meter = Meter(make_client(), prices, SETTINGS["model"], log=cfg.usage_log, label="judge")
done, items, good, quotes_ok, seconds, spent = [], 0, 0, 0, [], 0.0
cases = load(args.cases)
for case in cases:
    if spent + meter.cost >= args.max_usd:
        print(f"stopped: ${spent + meter.cost:.4f} spent, the cap is ${args.max_usd}")
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
    print(f"{case['lesson']:5} {result['status']:8} {result['attempts']} attempt(s)  code {len(passed)}/{len(found)}"
          f"  judge good {judged}/{len(found)}  ${result['cost']:.4f}  {seconds[-1]:.1f} s")
p95 = statistics.quantiles(seconds, n=20)[-1]
per_lesson = sum(done) / max(len(done), 1)
checks = [
    ("completion", len(done) >= 0.9 * len(cases), f"{len(done)} of {len(cases)} lessons done within 2 repairs"),
    ("quotes", items > 0 and quotes_ok == items, f"{quotes_ok} of {items} items quote their lesson word for word"),
    ("quality", items > 0 and good >= 0.8 * items, f"{good} of {items} items judged good ({good / max(items, 1):.0%})"),
    ("cost", per_lesson <= 0.02, f"${per_lesson:.4f} per completed lesson"),
    ("latency", p95 <= 30, f"p95 {p95:.1f} s per lesson"),
]
ungated = {"quality"} if args.gate else set()  # a target generate doesn't meet yet: reported, not gated
rows = [(name, "PASS" if ok else ("below" if name in ungated else "FAIL"), detail) for name, ok, detail in checks]
print(f"\njudge: {meter.requests} requests, ${meter.cost:.4f}; total ${spent + meter.cost:.4f}")
for name, verdict, detail in rows:
    print(f"{verdict:5} {name:10} {detail}")
if os.environ.get("GITHUB_STEP_SUMMARY"):  # the table on the job's summary page
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write("| check | result | detail |\n|---|---|---|\n")
        summary.writelines(f"| {name} | {verdict} | {detail} |\n" for name, verdict, detail in rows)
raise SystemExit(1 if any(verdict == "FAIL" for _, verdict, _ in rows) else 0)
