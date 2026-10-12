"""The layers between a lesson file and the approved bank. Two of them are switches in config.toml [guards], so an
experiment can turn one off and see what the next one catches; in normal use both are on.
  input   every search result the writer agent reads is screened first (8.1's screen, now inside the agent)
  output  the answer letter of every saved draft is placed by code (8.1's keys, now in the agent's save too), and a
          draft may name a site only if config.toml [guards] sites lists it: deny by default. Not "if the lesson has
          it": the attacker writes the lesson (Lab 8: the poisoned lesson's link passed that rule)
The others have no switch: the model layer (the system prompt), the tool layer (three tools, see
security/policy.toml) and the human layer (only qf review approves)."""

import json
import re
import tomllib

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT
from quizforge.meter import Meter
from quizforge.security import keys, screen

GUARDS = tomllib.loads((ROOT / "config.toml").read_text())["guards"]
ON, SITES = set(GUARDS["on"]), tuple(GUARDS["sites"])
_meters = {}


class Flagged(Exception):
    """A tool result the screen flagged: the writer gets this error instead of the text."""


def tool_result(cfg, found):
    """The input layer: the writer reads a search result only if the screen finds no instructions in it."""
    if "input" not in ON:
        return found
    if cfg.model not in _meters:
        prices = usage.load_prices(ROOT / "pricing.toml")
        _meters[cfg.model] = Meter(make_client(), prices, cfg.model, log=cfg.usage_log, label="screen")
    if screen.screen(_meters[cfg.model], json.dumps(found)).injection_suspected:
        raise Flagged(
            "withheld: this search result was flagged as a possible prompt injection. Write only from results "
            "that come back, and say so if a lesson can't be used."
        )
    return found


def draft(data, seed):
    """The output layer: where the correct answer sits is code's choice."""
    return keys.place(data, seed) if "output" in ON else data


LINK = re.compile(
    r"https?://[^\s)\"'>]+|\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|ai|dev|app|info|example)\b", re.IGNORECASE
)


def links(data):
    """The output layer's link rule: a question may name a site only if it is on the allowlist. Problems, or []."""
    if "output" not in ON:
        return []
    found = []
    for n, q in enumerate(data.questions, 1):
        for link in LINK.findall(f"{q.scenario} {q.a} {q.b} {q.c} {q.d} {q.why}"):
            host = link.lower().split("://")[-1].split("/")[0]
            if not any(host == site or host.endswith("." + site) for site in SITES):
                found.append(f"question {n}: {link} is not on the allowed sites ({', '.join(SITES)})")
    return found
