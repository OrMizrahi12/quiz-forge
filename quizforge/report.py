"""What each feature really costs, from the usage log, held against config.toml's [budget.*] tables.
Usage: python -m quizforge.report [--hours 24]   Exit code 1 when a feature is over its budget (a scheduler can
alert on it)."""
import argparse
import json
import re
import statistics
import tomllib
from datetime import datetime, timedelta, timezone

from quizforge.config import ROOT, load_config

FEATURES = [("generate", r"L\d\.\d v\d+ attempt \d+$"), ("judge", r"judge"), ("cache lab", r"cache lab"),
            ("tests", r"integration test")]


def feature(label):
    return next((name for name, pattern in FEATURES if re.match(pattern, label)), "other")


parser = argparse.ArgumentParser()
parser.add_argument("--hours", type=float, default=24)
args = parser.parse_args()
since = datetime.now(timezone.utc) - timedelta(hours=args.hours)
rows = [json.loads(line) for line in load_config().usage_log.read_text().splitlines()]
rows = [r for r in rows if "time" in r and datetime.fromisoformat(r["time"]) >= since]  # older rows had no time
budgets = tomllib.loads((ROOT / "config.toml").read_text()).get("budget", {})
over = []
print(f"{len(rows)} requests in the last {args.hours:g} h, ${sum(r['cost'] for r in rows):.4f}\n")
print("feature    requests      cost  per task  p95 s  cache read  budget")
for name in dict.fromkeys(feature(r["label"]) for r in rows):
    mine = [r for r in rows if feature(r["label"]) == name]
    cost, tokens = sum(r["cost"] for r in mine), sum(r["input"] + r["cache_write"] + r["cache_read"] for r in mine)
    tasks = sum(r["label"].endswith("attempt 1") for r in mine) if name == "generate" else len(mine)
    p95 = statistics.quantiles([r["seconds"] for r in mine], n=20)[-1] if len(mine) > 1 else mine[0]["seconds"]
    limit = budgets.get(name, {})
    breach = [f"{key} {value}" for key, value, now in (("usd_per_task", limit.get("usd_per_task"), cost / tasks),
                                                       ("p95_seconds", limit.get("p95_seconds"), p95))
              if value is not None and now > value]
    over += [f"{name}: {b}" for b in breach]
    verdict = ("OVER " + ", ".join(breach)) if breach else ("ok" if limit else "-")
    print(f"{name:10} {len(mine):8} {f'${cost:.4f}':>9} {f'${cost / tasks:.4f}':>9} {p95:6.1f} "
          f"{sum(r['cache_read'] for r in mine) / max(tokens, 1):11.0%}  {verdict}")
raise SystemExit(1 if over else 0)
