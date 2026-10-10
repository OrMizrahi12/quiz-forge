"""MCP by hand: connect to a server, list what it offers, call one tool. No model involved."""
import sys

import anyio
from mcp import Client
from mcp.types import TextContent

URL = sys.argv[1] if len(sys.argv) > 1 else "https://code.claude.com/docs/mcp"


async def main() -> None:
    async with Client(URL) as server:
        print("server:  ", server.server_info.name, "| protocol", server.protocol_version)
        caps = server.server_capabilities
        offers = [kind for kind in ("tools", "resources", "prompts") if getattr(caps, kind)]
        print("offers:  ", offers)

        tools = (await server.list_tools()).tools
        for tool in tools:
            inputs = ", ".join(tool.input_schema.get("properties", {}))
            print(f"\ntool {tool.name}({inputs})")
            print("    ", (tool.description or "").strip()[:70])
        if caps.resources:
            for resource in (await server.list_resources()).resources:
                print("\nresource", resource.uri)

        search = next(tool.name for tool in tools if tool.name.startswith("search"))
        result = await server.call_tool(search, {"query": "MCP installation scopes"})
        text = " ".join(b.text for b in result.content if isinstance(b, TextContent))
        print(f"\ncall {search} -> error={result.is_error}")
        print("    ", text[:240].replace("\n", " "))


anyio.run(main)
