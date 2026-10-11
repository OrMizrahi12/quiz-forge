import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from quizforge import retrieve, sources, usage, write
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter

BASE = replace(load_config(), max_tokens=1500)  # pinned: the budget math below assumes it, whatever config.toml says
PRICES = usage.load_prices(ROOT / "pricing.toml")
STEMS = [
    "A support team answers 3,000 short chat messages a day and wants each reply fast and cheap. Which tier fits?",
    "An analyst prepares one board report a quarter, where a wrong number would be costly. Which tier should she pick?",
]


def settings(tmp_path, **change):
    return replace(BASE, bank=tmp_path / "bank", usage_log=tmp_path / "usage.jsonl", **change)


def a_sentence():
    return next(
        line.strip()
        for c in retrieve.chunks(BASE.library)
        if c["source"].startswith("L1.3#")
        for line in c["text"].splitlines()
        if len(line.split()) > 10
    )


def questions(*stems):
    return [
        {
            "scenario": s,
            "a": "Haiku",
            "b": "Sonnet",
            "c": "Opus",
            "d": "Any tier",
            "answer": "A",
            "why": "The lesson says so.",
            "quote": a_sentence(),
        }
        for s in stems or STEMS
    ]


def reply(stop, *blocks):
    used = SimpleNamespace(
        input_tokens=4000, output_tokens=500, cache_creation_input_tokens=0, cache_read_input_tokens=0
    )
    return SimpleNamespace(stop_reason=stop, content=list(blocks), usage=used)


def text(words):
    return SimpleNamespace(type="text", text=words)


def use(n, name, **inputs):
    return SimpleNamespace(type="tool_use", id=f"toolu_{n}", name=name, input=inputs)


def saves(*stems):
    """The writer's two replies of one round: save the questions, then end its turn."""
    return [
        reply("tool_use", use(1, "save_questions", lesson_id="L1.3", questions=questions(*stems))),
        reply("end_turn", text("Saved.")),
    ]


def verdicts(*lines):
    """The checker's two replies of one round: check both quotes at once, then one line per question."""
    return [
        reply(
            "tool_use",
            use(7, "check_quote", lesson_id="L1.3", quote=a_sentence()),
            use(8, "check_quote", lesson_id="L1.3", quote=a_sentence()),
        ),
        reply("end_turn", text("\n".join(lines))),
    ]


SUPPORTED = ["Question 1: supported", "Question 2: supported"]
ONE_NOT = ["Question 1: supported", "Question 2: not supported: the quote doesn't back answer A"]


class Fake:
    """Writer and checker replies, each in its own queue: a request with the checker's system prompt is the checker's."""

    def __init__(self, writer, checker=()):
        self.writer, self.checker, self.requests, self.messages = list(writer), list(checker), [], self

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=4000)

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})  # as sent: the loop's list grows later
        return (self.checker if request["system"] == sources.REVIEW else self.writer).pop(0)

    def checker_requests(self):
        return [r for r in self.requests if r["system"] == sources.REVIEW]


def run(cfg, client):
    meter = Meter(client, PRICES, cfg.model, log=cfg.usage_log)
    return write.write(meter, cfg, "L1.3", out=lambda line: None), meter


def test_done_when_every_question_is_supported_and_it_waits_in_pending(tmp_path):
    cfg = settings(tmp_path)
    result, meter = run(cfg, Fake(saves(), verdicts(*SUPPORTED)))
    item = json.loads((cfg.bank / "pending" / "L1.3.json").read_text())
    assert (result.stopped, result.who, result.rounds, meter.requests) == ("done", "checker", 1, 4)
    assert item["verdicts"] == SUPPORTED and item["stopped"] == "done (checker, round 1)"
    assert all(q["section"].startswith("L1.3#") for q in item["questions"])
    assert [p.name for p in cfg.bank.iterdir()] == ["pending"]  # write never reaches approved/


def test_a_question_that_isnt_supported_is_revised_in_a_fresh_context(tmp_path):
    cfg = settings(tmp_path)
    better = STEMS[1].replace("costly", "very costly")
    client = Fake(saves() + saves(STEMS[0], better), verdicts(*ONE_NOT) + verdicts(*SUPPORTED))
    result, _ = run(cfg, client)
    assert (result.stopped, result.rounds) == ("done", 2)
    revise = [r for r in client.requests if r["system"] != sources.REVIEW][2]  # the writer's first request in round 2
    assert len(revise["messages"]) == 1 and ONE_NOT[1] in revise["messages"][0]["content"]
    assert result.job.questions[1]["scenario"] == better


def test_the_rounds_limit_stops_the_job_and_nothing_is_approved(tmp_path):
    cfg = settings(tmp_path, rounds=2)
    client = Fake(saves() * 2, verdicts(*ONE_NOT) * 2)
    result, meter = run(cfg, client)
    item = json.loads((cfg.bank / "pending" / "L1.3.json").read_text())
    assert (result.stopped, result.rounds, meter.requests) == ("rounds limit", 2, 8)
    assert item["verdicts"] == ONE_NOT and not (cfg.bank / "approved").exists()


def test_the_budget_covers_the_whole_job_writer_and_checker_together(tmp_path):
    # the writer's two requests cost $0.013; the checker's first could cost $0.0115 more: over $0.02, so it isn't sent
    cfg = settings(tmp_path, max_usd=0.02)
    client = Fake(saves(), verdicts(*SUPPORTED))
    result, meter = run(cfg, client)
    assert (result.stopped, result.who, meter.requests) == ("budget", "checker", 2)
    assert client.checker_requests() == [] and meter.cost <= 0.02


def test_the_turn_limit_stops_a_writer_that_never_saves(tmp_path):
    cfg = settings(tmp_path, max_turns=3)
    client = Fake([reply("tool_use", use(n, "search_library", query="tier", lesson_id="L1.3")) for n in range(3)])
    result, meter = run(cfg, client)
    assert (result.stopped, result.who, meter.requests) == ("turn limit", "writer", 3)
    assert not (cfg.bank / "pending" / "L1.3.json").exists()


@pytest.mark.parametrize("stop, said", [("max_tokens", "cut off"), ("refusal", "refused"), ("end_turn", "not saved")])
def test_a_writer_that_is_cut_off_refuses_or_ends_without_saving_stops_the_job(tmp_path, stop, said):
    result, meter = run(settings(tmp_path), Fake([reply(stop, text("Here are the questions"))]))
    assert (result.stopped, result.who, meter.requests) == (said, "writer", 1)


def test_the_checker_starts_with_a_clean_context(tmp_path):
    cfg = settings(tmp_path)
    client = Fake(saves(), verdicts(*SUPPORTED))
    result, _ = run(cfg, client)
    first = client.checker_requests()[0]
    assert first["messages"] == [{"role": "user", "content": sources.shown("L1.3", result.job.questions)}]
    assert [t["name"] for t in first["tools"]] == ["check_quote"]
    assert "Saved." not in json.dumps(first["messages"]) and "save_questions" not in json.dumps(first)


def test_a_repeated_stem_goes_back_to_the_writer_as_an_error_and_it_picks_another(tmp_path):
    cfg = settings(tmp_path)
    old = cfg.bank / "approved" / "L1.3.json"
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"lesson": "L1.3", "questions": questions(STEMS[0])}))
    fresh = (
        "A startup's founder must translate 40 legal contracts this week, and every clause matters. Which tier first?"
    )
    client = Fake([saves()[0]] + saves(fresh, STEMS[1]), verdicts(*SUPPORTED))
    result, _ = run(cfg, client)
    refusal = [r for r in client.requests if r["system"] != sources.REVIEW][1]["messages"][-1]["content"][0]
    assert refusal["is_error"] and "question 1: its scenario repeats one in approved/L1.3" in refusal["content"]
    assert result.stopped == "done" and result.job.questions[0]["scenario"] == fresh


def test_the_writer_searches_and_gets_search_result_blocks(tmp_path):
    client = Fake(
        [reply("tool_use", use(1, "search_library", query="smallest tier", lesson_id="L1.3"))] + saves(),
        verdicts(*SUPPORTED),
    )
    run(settings(tmp_path), client)
    result = client.requests[1]["messages"][-1]["content"][0]
    assert not result["is_error"] and {b["type"] for b in result["content"]} == {"search_result"}


def test_a_lesson_with_questions_waiting_is_not_written_again(tmp_path):
    cfg = settings(tmp_path)
    (cfg.bank / "pending").mkdir(parents=True)
    (cfg.bank / "pending" / "L1.3.json").write_text("{}")
    client = Fake([])
    with pytest.raises(write.Waiting, match="review them first"):
        run(cfg, client)
    assert client.requests == []


def test_every_request_of_the_job_is_logged(tmp_path):
    cfg = settings(tmp_path)
    run(cfg, Fake(saves(), verdicts(*SUPPORTED)))
    rows = [json.loads(line) for line in open(cfg.usage_log)]
    assert [r["label"] for r in rows] == ["L1.3 write round 1 writer"] * 2 + ["L1.3 write round 1 checker"] * 2
    assert all(r["counted"] == 4000 for r in rows)
