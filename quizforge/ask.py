"""qf ask: Claude answers a question about the library with the library server's tools. The SDK's MCP helper turns
each server tool into a tool Claude can call; Module 4's agent loop runs it, with its turn limit and budget."""

import anyio
from anthropic.lib.tools import ToolError
from anthropic.lib.tools.mcp import mcp_tool

from quizforge import agent

SYSTEM = (
    "You answer questions about the Quiz Forge lesson library, using only its tools. Name the lesson ids your "
    "answer relies on. If the tools find nothing that answers the question, say so instead of guessing."
)


async def ask(meter, cfg, question, library, out=print):
    """One question, answered through the server's tools. Returns the agent's Outcome (stopped, turns, text, calls)."""
    tools = {tool.name: mcp_tool(tool, library.session) for tool in (await library.list_tools()).tools}

    def act(call):  # runs in a worker thread; each tool call goes back to the event loop and on to the server
        out(f"  tool call  {call.name} {call.input}")
        try:
            return tools[call.name].call(call.input), False
        except KeyError:
            return f"no tool named {call.name!r}: the tools are {', '.join(tools)}", True
        except ToolError as error:
            return error.content, True

    limits = agent.Limits(max_turns=cfg.ask_turns, max_usd=cfg.ask_usd)
    schemas = [tool.to_dict() for tool in tools.values()]
    return await anyio.to_thread.run_sync(
        lambda: agent.run(meter, cfg, SYSTEM, schemas, act, question, limits, out=out)
    )
