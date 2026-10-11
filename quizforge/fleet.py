"""Several deployments, one view. Each deployment publishes a summary of itself (runs/status.json: counts, cost,
models, release); a coordinator reads only those files, never a deployment's library, bank, prompts or logs.
Usage: QF_HOME=<deployment> python -m quizforge.fleet publish
       python -m quizforge.fleet show <deployment folder> ...    (as many as you run)"""

import json
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import quizforge
from quizforge import usage
from quizforge.config import ROOT, load_config

STATUS = "runs/status.json"


def publish():
    """This deployment's summary: numbers and ids only, no question text, no lesson text, no key."""
    cfg, config = load_config(), tomllib.loads((ROOT / "config.toml").read_text())
    spent = usage.summary(cfg.usage_log)
    status = {
        "name": config.get("deployment", {}).get("name", ROOT.name),
        "release": quizforge.__version__,
        "models": {"writer": cfg.model, "generate": config["route"]["generate"]["model"]},
        "prompt": cfg.prompt,
        "lessons": len(json.loads((cfg.library / "MANIFEST.json").read_text())["lessons"]),
        "bank": {state: len(list((cfg.bank / state).glob("*.json"))) for state in ("pending", "approved", "declined")},
        "requests": spent["requests"],
        "usd": round(spent["cost"], 5),
        "updated": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (ROOT / STATUS).write_text(json.dumps(status, indent=1) + "\n")
    return status


def show(folders):
    print(
        f"{'deployment':12}{'release':>9}{'prompt':>8}{'lessons':>9}{'pending':>9}{'approved':>10}{'requests':>10}"
        f"{'usd':>10}  models"
    )
    for folder in folders:
        s = json.loads((Path(folder) / STATUS).read_text())
        print(
            f"{s['name']:12}{s['release']:>9}{s['prompt']:>8}{s['lessons']:>9}{s['bank']['pending']:>9}"
            f"{s['bank']['approved']:>10}{s['requests']:>10}{s['usd']:>10.4f}  {', '.join(s['models'].values())}"
        )


if __name__ == "__main__":
    if sys.argv[1:2] == ["publish"]:
        print(json.dumps(publish(), indent=1))
    else:
        show(sys.argv[2:])
