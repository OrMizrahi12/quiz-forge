import json
import re
from dataclasses import replace
from types import SimpleNamespace

from quizforge import batch, usage
from quizforge.config import ROOT, load_config
from quizforge.library import load_lesson

PRICES = usage.load_prices(ROOT / "pricing.toml")
BASE = load_config()


def settings(tmp_path):
    return replace(
        BASE, usage_log=tmp_path / "usage.jsonl", output_dir=tmp_path / "items", rejected_dir=tmp_path / "rejected"
    )


def sentence(lesson_id):
    return next(line for line in load_lesson(BASE.library, lesson_id).splitlines() if len(line.split()) > 10)


def reply_text(quote):
    q = {
        "scenario": "A team ships a feature on Friday. What should they check first?",
        "a": "The logs",
        "b": "The docs",
        "c": "The tests",
        "d": "The budget",
        "answer": "C",
        "why": "Tests show it works.",
        "quote": quote,
    }
    return json.dumps({"questions": [q] * BASE.questions})


def used():
    return SimpleNamespace(
        input_tokens=4000, output_tokens=500, cache_creation_input_tokens=0, cache_read_input_tokens=0
    )


def succeeded(cid, text):
    message = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(text=text)], usage=used())
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=message))


def errored(cid):
    error = SimpleNamespace(error=SimpleNamespace(type="invalid_request_error"))
    return SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="errored", error=error))


class BatchFake:
    """Batch results in the order given (not the order sent); realtime replies for the repairs."""

    def __init__(self, results, realtime=()):
        self.given, self.realtime, self.requests = results, list(realtime), []
        self.messages, self.batches = self, self

    def results(self, batch_id):
        return iter(self.given)

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=4000)

    def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(text=self.realtime.pop(0))],
            usage=used(),
            _request_id="req_test",
        )


def test_custom_ids_use_only_allowed_characters_and_round_trip():
    for lesson_id in ("L0.1", "L3.2", "L12.10"):
        cid = batch.custom_id(lesson_id, "v4")
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", cid)
        assert batch.lesson_of(cid) == lesson_id and batch.version_of(cid) == "v4"


def test_one_request_per_lesson_each_with_its_custom_id(tmp_path):
    reqs = list(batch.requests(BASE, ["L1.3", "L2.1"]))
    assert [r["custom_id"] for r in reqs] == ["L1_3-" + BASE.prompt, "L2_1-" + BASE.prompt]
    assert all(r["params"]["output_config"]["format"]["type"] == "json_schema" for r in reqs)
    assert "stream" not in reqs[0]["params"]


def test_results_in_any_order_are_matched_by_custom_id(tmp_path):
    good = {lesson: reply_text(sentence(lesson)) for lesson in ("L1.3", "L2.1", "L3.1")}
    shuffled = [succeeded(batch.custom_id(lesson, "v4"), good[lesson]) for lesson in ("L3.1", "L1.3", "L2.1")]
    rows = list(batch.collect(BatchFake(shuffled), settings(tmp_path), "msgbatch_test"))
    assert [(batch.lesson_of(cid), found) for cid, _, found, _, _ in rows] == [("L3.1", []), ("L1.3", []), ("L2.1", [])]


def test_a_passing_result_is_saved_at_the_batch_price(tmp_path):
    cfg = settings(tmp_path)
    client = BatchFake([succeeded("L1_3-v4", reply_text(sentence("L1.3")))])
    (row,) = batch.collect(client, cfg, "msgbatch_test")
    result = batch.finish(cfg, PRICES, client, *row, out=lambda line: None)
    assert result["status"] == "passed" and result["via"] == "batch" and client.requests == []
    assert result["cost"] == round(usage.cost(PRICES, cfg.model, used()) / 2, 6)
    assert (tmp_path / "items" / "L1.3.json").exists()


def test_a_failing_result_is_repaired_in_realtime_from_the_batch_reply(tmp_path):
    cfg = settings(tmp_path)
    bad = reply_text("A sentence the lesson never says, not even once.")
    client = BatchFake([succeeded("L1_3-v4", bad)], realtime=[reply_text(sentence("L1.3"))])
    (row,) = batch.collect(client, cfg, "msgbatch_test")
    result = batch.finish(cfg, PRICES, client, *row, out=lambda line: None)
    sent = client.requests[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[1]["content"] == bad and "quote not in the lesson" in sent[2]["content"]
    assert result["status"] == "passed" and result["attempts"] == 2


def test_an_errored_request_is_reported_and_not_saved_as_passed(tmp_path):
    cfg = settings(tmp_path)
    client = BatchFake([errored("L1_3-v4")])
    (row,) = batch.collect(client, cfg, "msgbatch_test")
    result = batch.finish(cfg, PRICES, client, *row, out=lambda line: None)
    assert result["status"] == "errored" and result["cost"] == 0.0
    assert not (tmp_path / "items" / "L1.3.json").exists() and (tmp_path / "rejected" / "L1.3.json").exists()
