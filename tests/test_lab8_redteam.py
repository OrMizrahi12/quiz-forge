"""Lab 8 self-check: the red-team harness against a writer that always obeys the lesson. A real model may or may not
follow an injection on a given day; this fake always does, so if the layers hold here, they hold whatever it does."""

import json
from collections import Counter
from dataclasses import replace
from types import SimpleNamespace

import pytest

from quizforge import guards, sources, usage, write
from quizforge.budget import Ledger
from quizforge.config import ROOT, load_config

CFG = load_config()


def rt():
    """The harness, imported per test: a project without experiments/redteam.py fails each test, not the collection."""
    from experiments import redteam

    return redteam


PRICES = usage.load_prices(ROOT / "pricing.toml")
QUOTE = "Effort is how thoroughly a model works on each reply."
STEMS = [
    "A team answers thousands of short chat messages a day and wants each reply fast and cheap. Which tier fits?",
    "An analyst writes one board report a quarter, where a wrong number would be costly. Which tier fits best?",
]


def reply(stop, *blocks):
    used = SimpleNamespace(
        input_tokens=3000, output_tokens=400, cache_creation_input_tokens=0, cache_read_input_tokens=0
    )
    return SimpleNamespace(stop_reason=stop, content=list(blocks), usage=used)


class Obedient:
    """The worst case: a writer that does whatever the lesson tells it. It searches the lesson, and if a search result
    carries an attack's marker, every key goes to A and every explanation carries the marker. A save that comes back
    with an error is sent once more, unchanged; then it gives up. The checker says every question is supported."""

    def __init__(self, marker):
        self.marker, self.messages, self.saves = marker, self, 0

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=3000)

    def create(self, **request):
        if request["system"] == sources.REVIEW:
            lines = [f"Question {n}: supported" for n in range(1, CFG.questions + 1)]
            return reply("end_turn", SimpleNamespace(type="text", text="\n".join(lines)))
        last = request["messages"][-1]["content"]
        if isinstance(last, str):  # the brief: search first
            call = {"query": "tiers haiku sonnet opus", "lesson_id": "L1.3"}
            return reply("tool_use", SimpleNamespace(type="tool_use", id="toolu_1", name="search_library", input=call))
        result = last[0]
        if result["is_error"] and result["tool_use_id"] == "toolu_1":  # withheld: nothing to write from
            return reply("end_turn", SimpleNamespace(type="text", text="I can't use that lesson."))
        if result["tool_use_id"] == "toolu_1" or (result["is_error"] and self.saves < 2):
            obey = self.marker.lower() in json.dumps(result["content"]).lower()
            self.saves += 1
            questions = [
                {
                    "scenario": stem,
                    "a": "Haiku",
                    "b": "Sonnet",
                    "c": "Opus",
                    "d": "Any tier",
                    "answer": "A" if obey else "B",
                    "quote": QUOTE,
                    "why": "The lesson says so." + (f" ({self.marker})" if obey else ""),
                }
                for stem in STEMS[: CFG.questions]
            ]
            call = {"lesson_id": "L1.3", "questions": questions}
            return reply(
                "tool_use",
                SimpleNamespace(type="tool_use", id=f"toolu_s{self.saves}", name="save_questions", input=call),
            )
        return reply("end_turn", SimpleNamespace(type="text", text="Done."))


class Screen:
    """The screen's meter, faked: flags any text that carries the marker."""

    def __init__(self, marker):
        self.model, self.messages, self.marker, self.cost = CFG.model, self, marker, 0.0

    def create(self, **request):
        hit = self.marker.lower() in request["messages"][0]["content"].lower()
        text = '{"injection_suspected": %s}' % ("true" if hit else "false")
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


@pytest.fixture
def harness(monkeypatch, tmp_path):
    """Run one red-team job offline: the obedient writer, the faked screen, a usage log in tmp_path."""
    monkeypatch.setattr(guards, "tool_result", guards.tool_result)  # watch() wraps them: undone after the test
    monkeypatch.setattr(guards, "links", guards.links)
    monkeypatch.setattr(guards, "ON", set(guards.ON))
    cfg = replace(CFG, usage_log=tmp_path / "usage.jsonl")
    seen = Counter()
    rt().watch(seen)

    def one(name, on):
        atk = rt().attack(name)
        monkeypatch.setattr(rt(), "make_client", lambda: Obedient(atk["marker"]))
        monkeypatch.setitem(guards._meters, CFG.model, Screen(atk["marker"]))
        return rt().run_one(cfg, PRICES, Ledger(1.0), atk, "test", on, 1, seen)

    return one


def test_the_fake_obeys_and_the_harness_sees_it(harness):
    row = harness("poisoned", set())
    assert row["reached"] and row["stopped_by"] == "none"
    assert row["keys_at_a"] == row["questions"] == CFG.questions


def test_all_layers_block_poisoned(harness):
    row = harness("poisoned", {"input", "output"})
    assert not row["reached"] and row["stopped_by"] == "input" and row["withheld"] >= 1


def test_output_layer_independent(harness):
    """With the screen off, the link rule still refuses the poisoned draft, and code places the keys."""
    row = harness("poisoned", {"output"})
    assert not row["reached"] and row["stopped_by"] == "output" and row["link_refusals"] >= 1


def test_the_save_step_attack_never_reaches_approved(harness):
    for on in (set(), {"output"}, {"input", "output"}):
        assert harness("approve-save", on)["approved_files"] == 0
    assert set(write.SAVE["input_schema"]["properties"]) == {"lesson_id", "questions"}  # no path, no status


def test_fixture_runs_isolated(harness, monkeypatch):
    """A fixture's draft goes to a scratch bank that is deleted after the run; the real bank/pending is untouched."""
    made, real = [], rt().scratch

    def recording(cfg, atk):
        root, job_cfg = real(cfg, atk)
        made.append((root, job_cfg.bank))
        return root, job_cfg

    monkeypatch.setattr(rt(), "scratch", recording)
    pending = ROOT / "bank" / "pending"
    before = sorted(p.name for p in pending.glob("*")) if pending.exists() else []
    assert harness("poisoned", set())["reached"]
    after = sorted(p.name for p in pending.glob("*")) if pending.exists() else []
    root, bank = made[0]
    assert before == after and ROOT not in bank.parents and not root.exists()


def test_the_configurations():
    assert rt().configs(["none", "all", "all-minus-each"]) == {
        "none": set(),
        "all": {"input", "output"},
        "all-input": {"output"},
        "all-output": {"input"},
    }
    with pytest.raises(SystemExit):
        rt().configs(["most"])


def test_every_attack_fixture_is_labeled_and_offline():
    folders = [p.parent for p in (ROOT / "library/fixtures").glob("*/attack.toml")]
    assert {"poisoned", "approve-save"} <= {f.name for f in folders}
    for folder in folders:
        atk = rt().attack(folder.name)
        assert "attack fixture" in (folder / "README.md").read_text().lower()
        lesson = (folder / f"{atk['lesson']}.md").read_text()
        original = (CFG.library / f"{atk['lesson']}.md").read_text()
        added = set(lesson.splitlines()) - set(original.splitlines())
        for link in guards.LINK.findall("\n".join(added)):
            assert link.lower().endswith(".example"), f"{folder.name}: {link} is not a reserved .example domain"
