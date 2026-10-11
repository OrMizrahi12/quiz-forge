"""The MCP server's contract: tool names, parameters and which are required. Hosts depend on them, so a change here
must be on purpose (pytest --update-snapshot), never by accident."""
import json
from pathlib import Path

import pytest
from mcp import Client

from mcp_server.server import mcp

SNAPSHOT = Path(__file__).parent / "snapshots/mcp_tools.json"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_the_tools_match_the_snapshot(request):
    async with Client(mcp) as client:
        tools = (await client.list_tools()).tools
    now = {tool.name: {"params": sorted(tool.input_schema["properties"]),
                       "required": sorted(tool.input_schema.get("required", []))} for tool in tools}
    if request.config.getoption("--update-snapshot"):
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(now, indent=1) + "\n")
    assert now == json.loads(SNAPSHOT.read_text()), "the MCP contract changed: hosts that call the old one break"
