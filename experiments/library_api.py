"""The library server inside an API app. Our own MCP client starts it over stdio, and the
SDK's helpers turn its tools into Tool Runner tools. (The API's MCP connector can't reach a
local stdio server.)"""
import sys

import anyio
from anthropic.lib.tools.mcp import async_mcp_tool, mcp_resource_to_content
from mcp import Client, StdioServerParameters

from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.usage import cost, load_prices

cfg = load_config()
PRICES = load_prices(ROOT / "pricing.toml")
SERVER = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
ASK = "Which lesson covers choosing a model tier, and what is one of its objectives? Cite its id."


async def main() -> None:
    claude = make_client(asynchronous=True)
    async with Client(SERVER) as library:
        tools = (await library.list_tools()).tools
        runner = claude.beta.messages.tool_runner(
            model=cfg.model,
            max_tokens=600,
            max_iterations=5,
            tools=[async_mcp_tool(tool, library.session) for tool in tools],
            messages=[{"role": "user", "content": ASK}],
        )
        requests, spent = 0, 0.0
        async for reply in runner:
            requests, spent = requests + 1, spent + cost(PRICES, cfg.model, reply.usage)
            for block in reply.content:
                if block.type == "tool_use":
                    print(f"tool call  {block.name} {block.input}")
                elif block.type == "text":
                    print(f"\n{block.text}\n")
        print(f"{requests} requests on {cfg.model}, ${spent:.4f}")

        # A resource is chosen by the app, not the model: read it, attach it, count it (free).
        lesson = mcp_resource_to_content(await library.read_resource("lesson://L1.3"))
        counted = await claude.messages.count_tokens(
            model=cfg.model, messages=[{"role": "user", "content": [lesson]}]
        )
        print(f"lesson://L1.3 as an attachment: {counted.input_tokens} tokens")


anyio.run(main)
