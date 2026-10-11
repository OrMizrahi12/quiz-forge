"""The layers between a lesson file and the approved bank. Two of them are switches in config.toml [guards], so an
experiment can turn one off and see what the next one catches; in normal use both are on.
  input   every search result the writer agent reads is screened first (8.1's screen, now inside the agent)
  output  the answer letter of every saved draft is placed by code (8.1's keys, now in the agent's save too)
The others have no switch: the model layer (the system prompt), the tool layer (three tools, see
security/policy.toml) and the human layer (only qf review approves)."""

import json
import tomllib

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT
from quizforge.meter import Meter
from quizforge.security import keys, screen

ON = set(tomllib.loads((ROOT / "config.toml").read_text())["guards"]["on"])
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
