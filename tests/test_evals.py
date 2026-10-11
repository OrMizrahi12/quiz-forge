"""The eval's own code, tested offline: each grader on a passing and a failing item, and kappa on known tables."""
from evals.calibrate import kappa
from evals.graders import grade, load
from quizforge.config import load_config

LIBRARY = load_config().library
ITEM = next(item for item in load() if item["id"] == "L3.2-gen1")  # passes every code grader


def failed(item):
    return [name for name, ok, _ in grade(item, LIBRARY) if not ok]


def test_a_good_item_passes_every_code_grader():
    assert failed(ITEM) == []


def test_each_grader_catches_its_flaw():
    assert failed({**ITEM, "item": {**ITEM["item"], "answer": "E"}}) == ["schema"]
    assert failed({**ITEM, "item": {**ITEM["item"], "quote": "A sentence that is not in the lesson."}}) == ["rules"]
    long_key = ITEM["item"]["c"] + " and check every other number and name on the page against the report too"
    assert failed({**ITEM, "item": {**ITEM["item"], "c": long_key}}) == ["key_length"]


def test_kappa():
    perfect = {("good", "good"): 5, ("good", "bad"): 0, ("bad", "good"): 0, ("bad", "bad"): 5}
    chance = {("good", "good"): 5, ("good", "bad"): 5, ("bad", "good"): 5, ("bad", "bad"): 5}
    assert kappa(perfect) == (1.0, 1.0) and kappa(chance) == (0.0, 0.5)
