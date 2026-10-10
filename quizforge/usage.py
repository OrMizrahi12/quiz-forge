import json
import tomllib
from pathlib import Path

FIELDS = (
    "time",
    "label",
    "model",
    "request_id",
    "counted",
    "input",
    "cache_write",
    "cache_read",
    "output",
    "cost",
    "seconds",
)


def load_prices(path) -> dict:
    return tomllib.loads(Path(path).read_text())["models"]


def cost(prices: dict, model: str, usage) -> float:
    """Dollars for one response, from its usage: input, output, cache writes and cache reads."""
    p = prices[model]
    write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    tokens_in = usage.input_tokens + p["cache_write"] * write + p["cache_read"] * read
    return (tokens_in * p["input"] + usage.output_tokens * p["output"]) / 1_000_000


def worst_case(prices: dict, model: str, counted: int, max_tokens: int) -> float:
    """The most a request can cost before it is sent: counted input plus max_tokens of output."""
    p = prices[model]
    return (counted * p["input"] + max_tokens * p["output"]) / 1_000_000


def log(path: Path, **row) -> dict:
    """Append one JSON line per request. Every field is required, so the log keeps one schema."""
    missing = set(FIELDS) - row.keys()
    if missing:
        raise ValueError(f"usage row is missing {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {k: row[k] for k in FIELDS}
    with open(path, "a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def summary(path: Path) -> dict:
    rows = [json.loads(line) for line in open(path)] if path.exists() else []
    by_label = {}
    for row in rows:
        lesson = row["label"].split()[0]
        by_label[lesson] = by_label.get(lesson, 0.0) + row["cost"]
    return {"requests": len(rows), "cost": sum(r["cost"] for r in rows), "by_lesson": by_label}
