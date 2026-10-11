"""Lab 6: the library server, finished. In memory: Client(mcp) talks to it with no process and no port."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import Client

from mcp_server import server
from mcp_server.server import mcp

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def library():
    async with Client(mcp) as client:
        yield client


@pytest.mark.anyio
async def test_tools_are_read_only_and_say_what_they_cant_do(library):
    for tool in (await library.list_tools()).tools:
        assert tool.title and tool.annotations.read_only_hint is True, tool.name
        assert "can't" in tool.description, f"{tool.name}: say what it can't do"


@pytest.mark.anyio
async def test_unknown_lesson_names_known_ids(library):
    wrong = await library.call_tool("get_objectives", {"lesson_id": "L9.9"})
    assert wrong.is_error
    assert "the library has" in wrong.content[0].text and "L1.3" in wrong.content[0].text


@pytest.mark.anyio
async def test_empty_query_says_what_to_send(library):
    empty = await library.call_tool("search_lessons", {"query": "  "})
    assert empty.is_error and "key words" in empty.content[0].text


@pytest.mark.anyio
async def test_prompt_stops_for_a_person(library):
    prompt = await library.get_prompt("write-items", {"lesson_id": "L1.3"})
    text = prompt.messages[0].content.text
    assert "bank/pending/" in text and "qf review" in text


@pytest.mark.anyio
async def test_tools_share_quizforge_functions(library, monkeypatch):
    monkeypatch.setattr(
        server,
        "search_library",
        lambda lib, q, lid=None: [{"source": "L0.0#stub", "content": [{"type": "text", "text": "from quizforge"}]}] * 3,
    )
    monkeypatch.setattr(server, "find_quote", lambda lib, lid, q: "from quizforge.sources")
    found = await library.call_tool("search_lessons", {"query": "anything"})
    assert found.structured_content["result"][0]["source"] == "L0.0#stub"
    quote = await library.call_tool("check_quote", {"lesson_id": "L1.3", "quote": "any four words here"})
    assert quote.content[0].text == "from quizforge.sources"


def test_server_never_prints():
    for path in (ROOT / "mcp_server").glob("*.py"):
        calls = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Call)]
        assert not [c for c in calls if getattr(c.func, "id", "") == "print"], f"{path.name} prints: stdout is the wire"


def test_paths_from_repo_root(tmp_path):
    code = "import mcp_server.server as s; print(s.LIBRARY.is_absolute(), (s.LIBRARY / 'MANIFEST.json').exists())"
    run = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        cwd=tmp_path,
        env={"PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
    )
    assert run.stdout.split() == ["True", "True"], run.stderr[-300:]
