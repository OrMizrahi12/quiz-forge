from types import SimpleNamespace

from quizforge import agent, usage
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter

CFG = load_config()
PRICES = usage.load_prices(ROOT / "pricing.toml")


def used(tokens_in=4000, tokens_out=500):
    return SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out, cache_creation_input_tokens=0, cache_read_input_tokens=0)


def reply(stop, *blocks):
    return SimpleNamespace(stop_reason=stop, content=list(blocks), usage=used())


def text(words):
    return SimpleNamespace(type="text", text=words)


def use(n, name="read_lesson", **inputs):
    return SimpleNamespace(type="tool_use", id=f"toolu_{n}", name=name, input=inputs)


class Script:
    """A stand-in client: the replies come in the order given (the last one repeats); every request is kept."""
    def __init__(self, *replies):
        self.replies, self.requests, self.messages = list(replies), [], self

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=4000)

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})   # as sent: the loop's list grows later
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def go(client, act=lambda call: ("ok", False), limits=agent.Limits()):
    meter = Meter(client, PRICES, CFG.model)
    return agent.run(meter, CFG, "system", [], act, "Do the task.", limits, out=lambda line: None), meter


def test_it_stops_when_claude_ends_its_turn():
    result, meter = go(Script(reply("end_turn", text("All saved."))))
    assert (result.stopped, result.turns, result.text, meter.requests) == ("done", 1, "All saved.", 1)


def test_it_stops_at_the_turn_limit():
    result, meter = go(Script(reply("tool_use", use(1))), limits=agent.Limits(max_turns=3))
    assert (result.stopped, result.turns, meter.requests) == ("turn limit", 3, 3)


def test_the_budget_is_checked_before_the_request_that_would_break_it():
    # each reply costs $0.0065; the worst case of the next one (4000 counted + 1500 max_tokens) is $0.0115
    result, meter = go(Script(reply("tool_use", use(1))), limits=agent.Limits(max_usd=0.015))
    assert (result.stopped, result.turns, meter.requests) == ("budget", 1, 1)
    assert meter.cost <= 0.015


def test_a_tool_that_raises_stop_ends_the_task_and_nothing_more_is_sent():
    def act(call):
        raise agent.Stop("declined")
    client = Script(reply("tool_use", use(1, "save_questions")), reply("end_turn", text("unreachable")))
    result, meter = go(client, act)
    assert (result.stopped, meter.requests) == ("declined", 1)


def test_a_reply_cut_off_at_max_tokens_stops_the_task():
    result, _ = go(Script(reply("max_tokens", text("Question 1: A team"))))
    assert result.stopped == "cut off"


def test_a_refusal_stops_the_task():
    result, _ = go(Script(reply("refusal")))
    assert result.stopped == "refused"


def test_every_tool_use_gets_its_result_in_one_user_message_in_order():
    client = Script(reply("tool_use", use(1), use(2, "check_quote")), reply("end_turn", text("done")))
    go(client, act=lambda call: (f"ran {call.name}", call.name == "check_quote"))
    results = client.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_1", "toolu_2"]
    assert [r["is_error"] for r in results] == [False, True]
