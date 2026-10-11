"""Quiz Forge as an MCP client: it starts the library server over stdio, as Claude Code does, and talks to it."""

import sys

from mcp import Client, StdioServerParameters

from quizforge.config import ROOT

SERVER = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=str(ROOT))


def connect(server=SERVER):
    """An MCP client for the library server: `async with connect() as library: ...`. The server runs as our own
    subprocess (the same Python), so its boundary is this process: no token, no port."""
    return Client(server)
