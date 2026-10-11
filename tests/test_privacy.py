import json
import shutil
from dataclasses import replace
from types import SimpleNamespace

import pytest

from quizforge import usage
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_one
from quizforge.memory import Memory
from quizforge.sanitize import minimize
from quizforge.security.redact import redact, redact_obj

READER = "## Reader questions\n\n> From Jordan Avery (jordan.avery@example.com, (212) 555-0142): one more example?\n"


def test_each_kind_is_replaced():
    assert redact("Write to sam@example.com or call (212) 555-0142.") == "Write to [EMAIL] or call [PHONE]."


def test_a_key_shaped_string_is_replaced():
    key = "sk-ant-" + "api03-" + "x" * 24  # built at runtime: no key-shaped literal in the repository
    assert redact(f"ANTHROPIC_API_KEY={key}") == "ANTHROPIC_API_KEY=[KEY]"


def test_nested_rows_are_redacted_and_other_values_kept():
    row = {"why": ["ask sam@example.com"], "attempts": 2}
    assert redact_obj(row) == {"why": ["ask [EMAIL]"], "attempts": 2}


def test_minimize_drops_the_reader_questions_and_keeps_the_lesson():
    lesson = "# L9.9\n\n## Facts\n\nHaiku is fast.\n\n" + READER + "\n## Sources\n\nThe docs.\n"
    assert minimize(lesson) == "# L9.9\n\n## Facts\n\nHaiku is fast.\n\n## Sources\n\nThe docs.\n"


class Capture:
    """A stand-in client that keeps the request and stops there."""

    def __init__(self):
        self.requests, self.messages = [], self

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=4000)

    def create(self, **request):
        self.requests.append(request)
        raise RuntimeError("captured")


def test_the_reader_never_reaches_the_request(tmp_path):
    base = load_config()
    shutil.copy(base.library / "MANIFEST.json", tmp_path / "MANIFEST.json")
    (tmp_path / "L2.1.md").write_text((base.library / "L2.1.md").read_text() + "\n" + READER)
    cfg = replace(base, library=tmp_path, usage_log=tmp_path / "usage.jsonl")
    client, route = Capture(), {"model": cfg.model, "max_tokens": cfg.max_tokens}
    with pytest.raises(RuntimeError):
        prices = usage.load_prices(ROOT / "pricing.toml")
        generate_one(cfg, prices, "L2.1", client=client, out=lambda line: None, route=route)
    sent = json.dumps(client.requests[0])
    assert "Jordan" not in sent and "example.com" not in sent and "555-0142" not in sent


def test_one_users_memory_cannot_reach_another_users(tmp_path):
    ana = Memory(tmp_path / "users" / "ana")
    with pytest.raises(ValueError):
        ana.path("/memories/../ben/notes.md")
