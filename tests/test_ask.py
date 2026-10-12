"""Lab 6: qf ask, Quiz Forge as an MCP client. The server runs in memory; a scripted stand-in plays Claude."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from mcp import Client

from mcp_server.server import mcp
from quizforge import usage
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter

CFG = replace(load_config(), model="claude-haiku-4-5-20251001")  # pinned: the budget test's math is at its $1/$5 prices
PRICES = usage.load_prices(ROOT / "pricing.toml")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def reply(stop, *blocks):
    used = SimpleNamespace(
        input_tokens=1200, output_tokens=150, cache_creation_input_tokens=0, cache_read_input_tokens=0
    )
    return SimpleNamespace(stop_reason=stop, content=list(blocks), usage=used)


def use(n, name, **inputs):
    return SimpleNamespace(type="tool_use", id=f"toolu_{n}", name=name, input=inputs)


class Script:
    """Replies in the order given (the last one repeats); every request is kept, as sent."""

    def __init__(self, *replies):
        self.replies, self.requests, self.messages = list(replies), [], self

    def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=1200)

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


async def run(script, cfg=CFG):
    from quizforge.ask import ask  # imported here: a missing module fails each test, not the whole file

    meter = Meter(script, PRICES, cfg.model)
    async with Client(mcp) as library:
        return await ask(meter, cfg, "Which lesson covers model tiers?", library, out=lambda line: None), meter


@pytest.mark.anyio
async def test_each_tool_call_goes_to_the_server():
    script = Script(
        reply("tool_use", use(1, "search_lessons", query="model tier latency")),
        reply("end_turn", SimpleNamespace(type="text", text="L1.3 covers it.")),
    )
    result, meter = await run(script)
    assert (result.stopped, result.calls, meter.requests) == ("done", ["search_lessons"], 2)
    assert sorted(t["name"] for t in script.requests[0]["tools"]) == ["check_quote", "get_objectives", "search_lessons"]
    sent = script.requests[1]["messages"][-1]["content"][0]
    assert sent["type"] == "tool_result" and not sent["is_error"] and "L1.3#" in str(sent["content"])


@pytest.mark.anyio
async def test_a_tool_error_goes_back_as_an_error():
    script = Script(
        reply("tool_use", use(1, "get_objectives", lesson_id="L9.9")),
        reply("end_turn", SimpleNamespace(type="text", text="No such lesson.")),
    )
    await run(script)
    sent = script.requests[1]["messages"][-1]["content"][0]
    assert sent["is_error"] and "the library has" in str(sent["content"])


@pytest.mark.anyio
async def test_stops_at_turn_limit():
    script = Script(reply("tool_use", use(1, "search_lessons", query="model tier")))
    result, meter = await run(script, replace(CFG, ask_turns=2))
    assert (result.stopped, meter.requests) == ("turn limit", 2)


@pytest.mark.anyio
async def test_stops_before_the_budget():
    script = Script(reply("tool_use", use(1, "search_lessons", query="model tier")))
    result, meter = await run(script, replace(CFG, ask_usd=0.001))
    assert (result.stopped, meter.requests) == ("budget", 0)


@pytest.mark.anyio
async def test_connect_starts_the_server_over_stdio():
    from quizforge.library_client import connect

    async with connect() as library:
        names = sorted(tool.name for tool in (await library.list_tools()).tools)
    assert names == ["check_quote", "get_objectives", "search_lessons"]


def test_ask_limits_come_from_config():
    assert CFG.ask_turns >= 2 and 0 < CFG.ask_usd <= 0.10
