from types import SimpleNamespace

import pytest

from quizforge.config import load_config
from quizforge.library import load_lesson
from quizforge.sanitize import clean
from quizforge.sources import NotChecked, check_quote, review, run, run_all, tools

CFG = load_config()


def a_sentence(lesson_id="L1.3"):
    return next(line.strip() for line in clean(load_lesson(CFG.library, lesson_id)).splitlines() if len(line.split()) > 10)


def call(n, **inputs):
    return SimpleNamespace(type="tool_use", id=f"toolu_{n}", name="check_quote", input=inputs)


def test_a_quote_from_the_lesson_is_found():
    assert check_quote(CFG.library, "L1.3", a_sentence()).startswith("found in L1.3")


def test_case_and_punctuation_do_not_matter():
    assert check_quote(CFG.library, "L1.3", a_sentence().upper().replace(",", "")).startswith("found")


def test_a_made_up_quote_is_not_found_and_the_closest_sentence_comes_back():
    result = check_quote(CFG.library, "L1.3", "Practice questions grow on purple trees in the spring.")
    assert result.startswith("not found in L1.3") and "Closest sentence" in result


def test_an_unknown_lesson_is_an_instructive_error():
    with pytest.raises(NotChecked, match="ids look like L1.3"):
        check_quote(CFG.library, "1.3", a_sentence())


def test_a_failure_goes_back_as_is_error_not_an_empty_string():
    result = run(CFG.library, call(1, lesson_id="L9.9", quote=a_sentence()))
    assert result["is_error"] is True and "unknown lesson id" in result["content"]
    assert result["tool_use_id"] == "toolu_1"


def test_a_missing_input_is_an_error_result_too():
    result = run(CFG.library, call(2, lesson_id="L1.3"))
    assert result["is_error"] is True and result["content"]


def test_all_results_come_back_in_the_order_of_the_calls():
    calls = [call(n, lesson_id="L1.3", quote=a_sentence() if n % 2 else "words that are not in the lesson at all") for n in range(6)]
    results = run_all(CFG.library, calls)
    assert [r["tool_use_id"] for r in results] == [c.id for c in calls]
    assert all(r["type"] == "tool_result" for r in results)


def test_the_tool_is_described_and_its_lesson_id_is_an_enum():
    (tool,) = tools(CFG.library)
    assert len(tool["description"].split(". ")) >= 3
    assert "L1.3" in tool["input_schema"]["properties"]["lesson_id"]["enum"]
    assert tool["input_schema"]["required"] == ["lesson_id", "quote"]


class ToolFake:
    """Turn 1: two check_quote calls in one reply. Turn 2: the verdicts."""
    def __init__(self, quote):
        self.quote, self.requests, self.messages = quote, [], self

    def create(self, **request):
        self.requests.append(request)
        used = SimpleNamespace(input_tokens=1000, output_tokens=100, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        if len(self.requests) == 1:
            uses = [SimpleNamespace(type="tool_use", id=f"toolu_{n}", name="check_quote",
                                    input={"lesson_id": "L1.3", "quote": self.quote}) for n in (1, 2)]
            return SimpleNamespace(stop_reason="tool_use", content=uses, usage=used)
        text = "Question 1: supported\nQuestion 2: not supported: the quote is about something else"
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)], usage=used)


def test_review_returns_every_result_in_one_user_message_and_reads_the_verdicts():
    question = {"scenario": "What?", "a": "1", "b": "2", "c": "3", "d": "4", "answer": "A", "why": "", "quote": a_sentence()}
    client = ToolFake(a_sentence())
    verdicts, calls, usages = review(client, CFG, "L1.3", [question, question], out=lambda line: None)
    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert [r["tool_use_id"] for r in second[2]["content"]] == ["toolu_1", "toolu_2"]
    assert calls == 2 and len(usages) == 2
    assert verdicts == ["Question 1: supported", "Question 2: not supported: the quote is about something else"]
