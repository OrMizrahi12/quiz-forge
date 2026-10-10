"""Four ways to give Claude a capability, measured by what each adds to a request's context.
count_tokens is free. It can't count server tools: that row comes from two tiny requests."""
import sys

import anyio
from mcp import Client, StdioServerParameters

from quizforge import sources
from quizforge.client import make_client
from quizforge.config import ROOT, load_config

cfg = load_config()
claude = make_client()
QUESTION = "Is this quote in lesson L1.3: 'Latency: how long you wait for the answer.'"
SKILL = (ROOT / "plugin/quiz-forge-tools/skills/write-exam-item/SKILL.md").read_text()


def counted(text=QUESTION, **extra) -> int:
    messages = [{"role": "user", "content": text}]
    return claude.messages.count_tokens(model=cfg.model, messages=messages, **extra).input_tokens


def sent(**extra) -> int:  # a real request, 16 tokens out: for what count_tokens can't count
    messages = [{"role": "user", "content": QUESTION}]
    reply = claude.messages.create(model=cfg.model, max_tokens=16, messages=messages, **extra)
    return reply.usage.input_tokens


async def mcp_tools() -> list[dict]:
    server = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
    async with Client(server) as library:
        listed = (await library.list_tools()).tools
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in listed]


bare, empty = counted(), counted(".")
fetch = [{"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 2}]
description = SKILL.split("description:", 1)[1].split("\n", 1)[0]
rows = [
    ("custom tool: check_quote (Lab 3)", counted(tools=sources.tools(cfg.library)) - bare),
    ("MCP: the library server's 3 tools", counted(tools=anyio.run(mcp_tools)) - bare),
    ("built-in: web fetch (2 requests)", sent(tools=fetch, tool_choice={"type": "none"}) - sent()),
    ("Skill: its description (always)", counted(description) - empty),
    ("Skill: all of SKILL.md (when used)", counted(SKILL) - empty),
]
print(f"{'a bare question':36} {bare:>6} tokens on {cfg.model}")
for name, extra in rows:
    print(f"{name:36} {extra:>+6}")
