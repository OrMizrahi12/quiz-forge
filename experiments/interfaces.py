"""One question, six interfaces: which of them know this project's rules? Each path asks once on Haiku 4.5, with no
tools, and bills to the API key in .env. A right answer names a person and python -m quizforge review."""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import anthropic
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-haiku-4-5-20251001"
QUESTION = "In this project, who may move an item into bank/approved/, and with which command? One sentence."


def right(text):
    t = text.lower()
    return "quizforge review" in t and any(w in t for w in ("person", "human", "you "))


def messages_api(system=None):
    extra = {"system": system} if system else {}
    reply = anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=200, messages=[{"role": "user", "content": QUESTION}], **extra
    )
    cost = reply.usage.input_tokens * 1e-6 + reply.usage.output_tokens * 5e-6  # Haiku 4.5: $1 / $5 per million
    return reply.content[0].text, reply.usage.input_tokens, cost


def agent_sdk(sources):
    async def run():
        options = ClaudeAgentOptions(model=MODEL, cwd=str(ROOT), setting_sources=sources, tools=[], max_turns=2)
        async for message in query(prompt=QUESTION, options=options):
            if isinstance(message, ResultMessage):
                result = message
        used = result.usage or {}
        tokens = sum(used.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        return result.result or "", tokens, result.total_cost_usd

    return asyncio.run(run())


def claude_code(bare):
    flags = ["--bare"] if bare else []
    out = subprocess.run(
        [
            "claude",
            *flags,
            "-p",
            QUESTION,
            "--model",
            MODEL,
            "--tools",
            "",
            "--output-format",
            "json",
            "--no-session-persistence",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    data = json.loads(out.stdout)
    used = data.get("usage", {})
    tokens = sum(used.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return data.get("result", ""), tokens, data.get("total_cost_usd", 0)


PATHS = [
    ("Messages API, no system prompt", lambda: messages_api()),
    ("Messages API, CLAUDE.md as the system prompt", lambda: messages_api((ROOT / "CLAUDE.md").read_text())),
    ("Agent SDK, setting_sources=[]", lambda: agent_sdk([])),
    ('Agent SDK, setting_sources=["project"]', lambda: agent_sdk(["project"])),
    ("claude -p --bare", lambda: claude_code(bare=True)),
    ("claude -p", lambda: claude_code(bare=False)),
]


def main():
    load_dotenv(ROOT / ".env")
    print(f"{'path':46} {'right':6} {'input tokens':>12} {'cost':>8} {'time':>6}")
    for name, ask in PATHS:
        start = time.perf_counter()
        text, tokens, cost = ask()
        print(
            f"{name:46} {'yes' if right(text) else 'no':6} {tokens:>12,} ${cost:>7.4f} {time.perf_counter() - start:>5.1f}s"
        )
        if os.environ.get("SHOW"):
            print("   ", text.strip().replace("\n", " ")[:160])


if __name__ == "__main__":
    sys.exit(main())
