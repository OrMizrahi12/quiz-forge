"""What each feature really costs, from the usage log, held against config.toml's [budget.*] tables.
Usage: python -m quizforge report [--since 1d] [--by feature|model]   Exit code 1 when a feature is over its budget
(a scheduler or CI can alert on it)."""
import argparse
import json
import re
import statistics
import tomllib
from datetime import UTC, datetime, timedelta

from quizforge.config import ROOT, load_config

FEATURES = [("generate", r"L\d\.\d v\d+ attempt \d+$"), ("judge", r"judge"), ("cache lab", r"cache lab"),
            ("tests", r"integration test")]


def feature(label):
    return next((name for name, pattern in FEATURES if re.match(pattern, label)), "other")


def hours(since):
    """'1d', '12h' or '90m' as hours."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([dhm])", since)
    if not match:
        raise SystemExit(f"--since takes a number and d, h or m, e.g. 1d or 12h (got {since!r})")
    return float(match[1]) * {"d": 24, "h": 1, "m": 1 / 60}[match[2]]


def rows_since(log, window_hours, now=None):
    since = (now or datetime.now(UTC)) - timedelta(hours=window_hours)
    rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return [r for r in rows if "time" in r and datetime.fromisoformat(r["time"]) >= since]  # older rows had no time


def report(rows, budgets, by="feature", out=print):
    """One line per feature (or model), each budget breach marked. Returns the breaches."""
    over, key = [], (lambda r: feature(r["label"])) if by == "feature" else (lambda r: r["model"])
    out(f"{len(rows)} requests, ${sum(r['cost'] for r in rows):.4f}\n")
    out(f"{by:26} requests      cost  per task  p95 s  cache read  budget")
    for name in dict.fromkeys(key(r) for r in rows):
        mine = [r for r in rows if key(r) == name]
        cost, tokens = sum(r["cost"] for r in mine), sum(r["input"] + r["cache_write"] + r["cache_read"] for r in mine)
        generating = by == "feature" and name == "generate"
        tasks = max(sum(r["label"].endswith("attempt 1") for r in mine), 1) if generating else len(mine)
        p95 = statistics.quantiles([r["seconds"] for r in mine], n=20)[-1] if len(mine) > 1 else mine[0]["seconds"]
        limit = budgets.get(name, {}) if by == "feature" else {}
        breach = [f"{field} {value}" for field, value, now in (("usd_per_task", limit.get("usd_per_task"), cost / tasks),
                                                                ("p95_seconds", limit.get("p95_seconds"), p95))
                  if value is not None and now > value]
        over += [f"{name}: {b}" for b in breach]
        verdict = ("OVER " + ", ".join(breach)) if breach else ("ok" if limit else "-")
        out(f"{name:26} {len(mine):8} {f'${cost:.4f}':>9} {f'${cost / tasks:.4f}':>9} {p95:6.1f} "
            f"{sum(r['cache_read'] for r in mine) / max(tokens, 1):11.0%}  {verdict}")
    return over


def run(since="1d", by="feature", out=print):
    budgets = tomllib.loads((ROOT / "config.toml").read_text()).get("budget", {})
    over = report(rows_since(load_config().usage_log, hours(since)), budgets, by, out)
    return 1 if over else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="1d")
    parser.add_argument("--by", choices=["feature", "model"], default="feature")
    args = parser.parse_args()
    raise SystemExit(run(args.since, args.by))
