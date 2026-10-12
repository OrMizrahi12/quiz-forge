"""What a release is made of: the version, the commit, the config's hash, each feature's model (checked against the
Models API and models.lock.toml) and each prompt's locked version. --check fails on an alias, a model missing from
the lock, or a model the API says is deprecated or retired.
Usage: python -m quizforge.release [--check]"""

import hashlib
import subprocess
import sys
import tomllib
from datetime import date

import quizforge
from quizforge.client import make_client
from quizforge.config import CODE, ROOT
from quizforge.prompts import locked

NOTICE = 60  # days: a deprecation notice comes at least this far ahead of a retirement


def features(config):
    """Each feature's model id, as config.toml sets it."""
    found = {
        "writer": config["model"]["writer"],
        "reviewer": config["model"]["reviewer"],
        "judge": config["judge"]["model"],
    }
    return found | {f"route.{name}": route["model"] for name, route in config.get("route", {}).items()}


def check(model, entry, info, today):
    """(status, problem) for one model: the API's answer and the lock's dates, together."""
    if info.id != model:
        return "alias", f"{model} is an alias for {info.id}: pin the snapshot"
    if entry is None:
        return info.lifecycle, f"{model} is not in models.lock.toml"
    if info.lifecycle != "active":
        return info.lifecycle, f"{model} is {info.lifecycle}, retiring {info.retires_at}: upgrade it (docs/runbook.md)"
    days = (entry["retires_not_before"] - today).days
    return ("active, watch" if days < NOTICE else "active"), None


def manifest(client, today=None):
    text = (ROOT / "config.toml").read_text()
    config, lock = tomllib.loads(text), tomllib.loads((ROOT / "models.lock.toml").read_text())
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=CODE, capture_output=True, text=True, check=True
    )
    config_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    lines = [f"quiz-forge {quizforge.__version__} at {commit.stdout.strip()}, config.toml {config_hash}"]
    problems = []
    for feature, model in features(config).items():
        entry = lock.get(model)
        status, problem = check(model, entry, client.models.retrieve(model), today or date.today())
        problems += [problem] if problem else []
        lines.append(
            f"{feature:15} {model:27} {status:14} retires not before {entry['retires_not_before'] if entry else '?'}"
        )
    for name, version in [("item_writer", config["prompt"]["item_writer"]), ("judge", config["judge"]["prompt"])]:
        lines.append(
            f"prompt {name:11} {version:3} sha256 {locked(ROOT / 'prompts' / name).get(version, 'NOT LOCKED')[:12]}"
        )
    return lines, problems


if __name__ == "__main__":
    lines, problems = manifest(make_client())
    print("\n".join(lines + [f"PROBLEM {p}" for p in problems]))
    sys.exit(1 if problems and "--check" in sys.argv else 0)
