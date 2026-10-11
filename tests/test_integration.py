"""Integration: one real boundary per test, run on purpose (pytest -m integration). The API test needs a key."""
import os

import pytest
from dotenv import load_dotenv

from quizforge import library_client, usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter

load_dotenv()
MODEL, HI = "claude-haiku-4-5-20251001", [{"role": "user", "content": "Say hi."}]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_the_api_answers_and_the_meter_logs_it():
    meter = Meter(make_client(), usage.load_prices(ROOT / "pricing.toml"), MODEL, log=load_config().usage_log,
                  label="integration test")
    counted = meter.count_tokens(model=MODEL, messages=HI)
    reply = meter.messages.create(model=MODEL, max_tokens=20, messages=HI)
    assert counted.input_tokens > 0 and reply._request_id.startswith("req_") and meter.cost > 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_the_mcp_server_starts_as_a_process():
    async with library_client.connect() as library:
        tools = (await library.list_tools()).tools
    assert sorted(tool.name for tool in tools) == ["check_quote", "get_objectives", "search_lessons"]
