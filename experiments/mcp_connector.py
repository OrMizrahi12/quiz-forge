"""The MCP connector: Anthropic's side connects to a remote MCP server for us, during the request.
No MCP client in our code. The server must be reachable over public HTTPS; only its tools are used."""
import sys

import anthropic

from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.usage import cost, load_prices

cfg = load_config()
PRICES = load_prices(ROOT / "pricing.toml")
URL = sys.argv[1] if len(sys.argv) > 1 else "https://platform.claude.com/docs/mcp"
ASK = "According to the Claude docs, what can the MCP connector not connect to? Two sentences."

try:
    reply = make_client().beta.messages.create(
        model=cfg.model,
        max_tokens=500,
        betas=["mcp-client-2025-11-20"],
        mcp_servers=[{"type": "url", "url": URL, "name": "claude-docs"}],
        tools=[{
            "type": "mcp_toolset",
            "mcp_server_name": "claude-docs",
            "default_config": {"enabled": False},  # allow-list: only the two read tools
            "configs": {"search_docs": {"enabled": True}, "get_doc": {"enabled": True}},
        }],
        messages=[{"role": "user", "content": ASK}],
    )
except anthropic.BadRequestError as error:  # the request is refused: print why
    sys.exit(f"{error.status_code}: {error.body['error']['message']}")

for block in reply.content:
    if block.type == "mcp_tool_use":
        print(f"mcp_tool_use     {block.name} {block.input}")
    elif block.type == "mcp_tool_result":
        text = " ".join(part.text for part in block.content if part.type == "text")
        print(f"mcp_tool_result  {len(text):,} characters")
    elif block.type == "text":
        print(f"\n{block.text}\n")
u = reply.usage
print(f"{u.input_tokens:,} tokens in, {u.output_tokens:,} out, ${cost(PRICES, cfg.model, u):.4f} on {cfg.model}")
