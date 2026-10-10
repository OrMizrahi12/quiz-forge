"""The library server, tested in memory: Client(mcp) talks to it with no process and no port."""
import pytest
from mcp import Client, MCPError

from mcp_server.server import mcp

SENTENCE = "Haiku, Sonnet or Opus, the size of Claude you pick, trading capability against speed"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def library():
    async with Client(mcp, raise_exceptions=True) as client:
        yield client


@pytest.mark.anyio
async def test_three_tools_with_their_inputs(library):
    tools = {t.name: t for t in (await library.list_tools()).tools}
    assert sorted(tools) == ["check_quote", "get_objectives", "search_lessons"]
    assert tools["search_lessons"].input_schema["required"] == ["query"]
    assert tools["check_quote"].input_schema["required"] == ["lesson_id", "quote"]


@pytest.mark.anyio
async def test_search_and_objectives(library):
    found = await library.call_tool("search_lessons", {"query": "model tier latency"})
    sections = found.structured_content["result"]
    assert len(sections) == 3 and sections[0]["source"].startswith("L1.3#")
    objectives = await library.call_tool("get_objectives", {"lesson_id": "L1.3"})
    assert len(objectives.structured_content["result"]) == 3


@pytest.mark.anyio
async def test_check_quote_finds_it_and_refuses_two_words(library):
    found = await library.call_tool("check_quote", {"lesson_id": "L1.3", "quote": SENTENCE})
    assert found.content[0].text == "found in L1.3"
    short = await library.call_tool("check_quote", {"lesson_id": "L1.3", "quote": "two words"})
    assert short.is_error and "too short" in short.content[0].text


@pytest.mark.anyio
async def test_lessons_are_resources(library):
    read = await library.read_resource("lesson://L1.3")
    assert "Haiku" in read.contents[0].text
    with pytest.raises(MCPError):
        await library.read_resource("lesson://L9.9")


@pytest.mark.anyio
async def test_write_items_prompt(library):
    prompt = await library.get_prompt("write-items", {"lesson_id": "L1.3"})
    assert "check_quote" in prompt.messages[0].content.text
