"""Prompt caching, tested offline: where the breakpoint goes, what writes and reads cost, what the meter counts.
The live self-check (a second identical request reads the cache) is marked integration."""
import os
from types import SimpleNamespace

import pytest
from dotenv import load_dotenv

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import cached_turn
from quizforge.library import load_lesson
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt

load_dotenv()
PRICES = usage.load_prices(ROOT / "pricing.toml")
HAIKU = "claude-haiku-4-5-20251001"


def used(write=0, read=0, hour=0):
    return SimpleNamespace(input_tokens=0, output_tokens=0, cache_creation_input_tokens=write,
                           cache_read_input_tokens=read, cache_creation=SimpleNamespace(ephemeral_1h_input_tokens=hour))


def test_the_breakpoint_is_on_the_lesson_not_on_the_ask():
    lesson, ask = cached_turn("L2.4", "Facts.", 2)
    assert lesson["cache_control"] == {"type": "ephemeral"} and lesson["text"].endswith("</lesson>")
    assert "cache_control" not in ask and ask["text"] == "Write 2 questions."


def test_writes_cost_more_than_input_and_reads_far_less():
    million = [usage.cost(PRICES, HAIKU, u) for u in (used(write=10**6), used(write=10**6, hour=10**6),
                                                       used(read=10**6))]
    assert [round(dollars, 4) for dollars in million] == [1.25, 2.0, 0.1]  # input is $1.00 per million


def test_the_meter_counts_every_input_token():
    reply = SimpleNamespace(usage=SimpleNamespace(input_tokens=24, output_tokens=0, cache_creation_input_tokens=0,
                                                  cache_read_input_tokens=6340))
    meter = Meter(SimpleNamespace(messages=SimpleNamespace(create=lambda **request: reply)), PRICES, HAIKU)
    meter.messages.create(model=HAIKU)
    assert meter.tokens_in == 6364


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_a_second_identical_request_reads_the_cache():
    cfg = load_config()
    meter = Meter(make_client(), PRICES, HAIKU, log=cfg.usage_log, label="integration test cache")
    request = {"model": HAIKU, "max_tokens": 20, "system": for_schema(load_prompt(cfg.prompts, cfg.prompt)),
               "messages": [{"role": "user", "content": cached_turn("L2.4", load_lesson(cfg.library, "L2.4"), 2)}]}
    meter.messages.create(**request)
    assert meter.messages.create(**request).usage.cache_read_input_tokens > 4096
