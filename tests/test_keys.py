"""Key placement in code, offline: the right option keeps its text, and the letters spread."""

from quizforge.schema import Questions
from quizforge.security.keys import place

ITEM = {
    "scenario": "Which tier?",
    "a": "Haiku",
    "b": "Sonnet",
    "c": "Opus",
    "d": "None",
    "answer": "A",
    "why": "Speed and volume.",
    "quote": "Haiku is small and fast.",
}


def test_the_right_option_keeps_its_text():
    data = place(Questions(questions=[dict(ITEM)] * 3), seed="L1.3")
    for q in data.questions:
        assert getattr(q, q.answer.lower()) == "Haiku" and sorted([q.a, q.b, q.c, q.d]) == [
            "Haiku",
            "None",
            "Opus",
            "Sonnet",
        ]


def test_every_key_at_a_is_spread_out():
    keys = [q.answer for q in place(Questions(questions=[dict(ITEM)] * 40), seed="L1.3").questions]
    assert keys.count("A") < 20 and len(set(keys)) == 4


def test_the_same_seed_gives_the_same_order():
    first = place(Questions(questions=[dict(ITEM)] * 5), seed="L2.1").model_dump()
    assert place(Questions(questions=[dict(ITEM)] * 5), seed="L2.1").model_dump() == first
