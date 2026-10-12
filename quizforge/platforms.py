"""The platform Quiz Forge runs on ([platform] name in config.toml, default anthropic), the client class for it, and
what would break there. Usage: python -m quizforge.platforms   (every platform, Quiz Forge's own uses checked)"""
import tomllib

import anthropic

from quizforge.config import ROOT

PLATFORMS = tomllib.loads((ROOT / "quizforge/platforms.toml").read_text())
USES = {   # the features Quiz Forge uses, and where
    "structured_outputs": "generate, repair, the screen (2.4, 8.1)",
    "files": "qf evidence (3.4)",
    "batches": "qf batch (3.5)",
    "models": "qf model, the pinned-model check (1.6)",
}


def current():
    config = tomllib.loads((ROOT / "config.toml").read_text())
    return config.get("platform", {}).get("name", "anthropic")


def base_client(asynchronous=False, name=None):
    """The SDK client class for the platform; its credentials come from that platform's environment variables."""
    cls = PLATFORMS[name or current()]["client"]
    return getattr(anthropic, ("Async" if asynchronous else "") + cls)()


def gaps(name):
    return {feature: USES[feature] for feature in PLATFORMS[name]["missing"]}


if __name__ == "__main__":
    for name, p in PLATFORMS.items():
        broken = gaps(name)
        print(f"{name:10} {p['operator']:24} billed by {p['billing']:18} residency: {p['residency']}")
        if not broken:
            print(f"{'':10} ok      everything Quiz Forge uses")
        for feature, where in broken.items():
            print(f"{'':10} breaks  {feature:19} {where}")
