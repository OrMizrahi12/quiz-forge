import json
from types import SimpleNamespace

import pytest

from quizforge.repair import Refused, RepairFailed, write_checked
from quizforge.schema import Questions
from quizforge.validate import loads_lenient, problems

LESSON = "Context: the background Claude can't know: the situation, why you need the result."
GOOD = {
    "scenario": "A manager gets a generic list from Claude. What was missing?",
    "a": "Context",
    "b": "Format",
    "c": "Audience",
    "d": "Task",
    "answer": "A",
    "why": "Claude didn't know the situation.",
    "quote": "Context: the background Claude can't know",
}


def questions(**change):
    return Questions(questions=[{**GOOD, **change}])


def test_good_questions_pass():
    assert problems(questions(), LESSON, 1) == []


def test_a_quote_not_in_the_lesson_fails():
    found = problems(questions(quote="Context is everything."), LESSON, 1)
    assert found == ["question 1: quote not in the lesson"]


def test_two_same_options_fail():
    found = problems(questions(b="context"), LESSON, 1)
    assert found == ["question 1: two options are the same"]


def test_the_wrong_count_fails():
    assert problems(questions(), LESSON, 2) == ["expected 2 questions, got 1"]


def test_a_fence_is_stripped():
    text = "```json\n" + json.dumps({"questions": [GOOD]}) + "\n```"
    assert loads_lenient(text).questions[0].answer == "A"


class Scripted:
    """A stand-in client: returns the replies it was given, in order, and counts calls."""

    def __init__(self, *replies):
        self.replies, self.calls, self.messages = list(replies), 0, self

    def create(self, **request):
        self.calls += 1
        return self.replies.pop(0)


def reply(stop_reason="end_turn", **change):
    text = questions(**change).model_dump_json()
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(text=text)], usage=SimpleNamespace(input_tokens=100)
    )


def write(client):
    return write_checked(client, "model", "rules", "ask", LESSON, 1)


def test_a_retry_repairs_it():
    client = Scripted(reply(quote="Made up."), reply())
    assert write(client)[1] == 2 and client.calls == 2


def test_repair_stops_at_the_limit():
    client = Scripted(*[reply(quote="Made up.") for _ in range(5)])
    with pytest.raises(RepairFailed):
        write(client)
    assert client.calls == 3


def test_a_refusal_is_not_retried():
    client = Scripted(reply(stop_reason="refusal"), reply())
    with pytest.raises(Refused):
        write(client)
    assert client.calls == 1
