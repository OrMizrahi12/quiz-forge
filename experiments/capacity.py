"""Northwind's quarter, from our own logs: what one lesson costs on generate's route (the usage log), how many items
come out good (the last eval gate), and the load against the limits from residency.py (runs/limits.json).
Usage: python -m experiments.capacity [approved items per quarter]"""
import json
import re
import sys
import tomllib

from quizforge.config import ROOT, load_config

APPROVED = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
NIGHTS, HOURS = 65, 8                   # bulk runs: 13 weeks of weeknights, 8 hours each
cfg = load_config()
route = tomllib.loads((ROOT / "config.toml").read_text())["route"]["generate"]["model"]
rows = [json.loads(line) for line in (ROOT / "runs/usage.jsonl").read_text().splitlines()]
gen = [r for r in rows if r["model"] == route and re.match(r"L\d\.\d v\d+ attempt \d+$", r["label"])]
runs = sum(r["label"].endswith("attempt 1") for r in gen)   # each lesson run starts with attempt 1
per_run = {k: sum(r[k] for r in gen) / runs for k in ("input", "cache_read", "output", "cost")}
gate = json.loads((ROOT / "runs/last-gate.json").read_text())["totals"]
good = gate["good"] / gate["items"]     # a reviewer approves at most what the judge calls good
done = gate["done"] / gate["lessons"]
lesson_runs = APPROVED / (cfg.questions * good * done)
limits = json.loads((ROOT / "runs/limits.json").read_text())
tpm_in = lesson_runs / NIGHTS * (per_run["input"] + per_run["cache_read"]) / (HOURS * 60)
cost = lesson_runs * per_run["cost"]

print(f"route: {route}, {runs} lesson runs in the usage log; gate {gate['done']}/{gate['lessons']} done, "
      f"{gate['good']}/{gate['items']} items judged good")
print(f"one lesson run: {per_run['input'] + per_run['cache_read']:,.0f} input tokens, {per_run['output']:,.0f} "
      f"output, ${per_run['cost']:.5f}")
print(f"\n{'per quarter':32}{'value':>14}")
for name, value in [("approved items wanted", f"{APPROVED:,}"),
                    ("lesson runs needed", f"{lesson_runs:,.0f}"),
                    ("lesson runs per night", f"{lesson_runs / NIGHTS:,.0f}"),
                    ("input tokens per minute (night)", f"{tpm_in:,.0f}"),
                    (f"  limit ({limits['date']})", f"{limits['input-tokens']:,}"),
                    ("generate cost, realtime", f"${cost:,.2f}"),
                    ("  US-only (1.1x)", f"${cost * 1.1:,.2f}"),
                    ("  US-only, Batch (50% off)", f"${cost * 1.1 * 0.5:,.2f}")]:
    print(f"{name:32}{value:>14}")
