"""Session hygiene, measured: four reviews in one ClaudeSDKClient session vs four fresh query() calls, each with the
reviewer's options (what sdk_review.py does). Per review: the context the model already holds when the review starts
(the input tokens of its first request), the cost, and whether the answer names another item."""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, ResultMessage, query
from dotenv import load_dotenv

from reviewer.sdk_review import ROOT, SKILL, options

HAIKU = "claude-haiku-4-5-20251001"  # this measures sessions, not review quality: the cheaper model will do
ITEMS = ["bank/pending/L1.3.json", "bank/pending/L2.1.json", "bank/declined/L2.2.json", "bank/approved/L1.3.json"]


def prompt(path):
    return f"Review {path} with the {SKILL} checklist. Answer pass or fail and the main reason, in one line."


def tokens(usage):
    used = usage or {}
    return sum(used.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


async def review(messages, path):
    """Read one review's messages: the context at its first request, and the final result."""
    start = None
    async for message in messages:
        if isinstance(message, AssistantMessage) and start is None:
            start = tokens(message.usage)
        if isinstance(message, ResultMessage):
            result = message
    own = Path(path).stem
    leaks = sorted({Path(p).stem for p in ITEMS if Path(p).stem != own and Path(p).stem in (result.result or "")})
    return start or 0, result.total_cost_usd, leaks


async def one_session():
    rows, spent = [], 0.0
    async with ClaudeSDKClient(options=options(model=HAIKU)) as client:
        for path in ITEMS:
            await client.query(prompt(path))
            start, total, leaks = await review(client.receive_response(), path)
            rows.append((path, start, total - spent, leaks))  # in one session the reported cost is the running total
            spent = total
    return rows


async def fresh_sessions():
    rows = []
    for path in ITEMS:
        start, cost, leaks = await review(query(prompt=prompt(path), options=options(model=HAIKU)), path)
        rows.append((path, start, cost, leaks))
    return rows


def main():
    load_dotenv(ROOT / ".env")
    for name, run in (("one session, four prompts", one_session), ("four fresh sessions", fresh_sessions)):
        print(f"{name}: context when each review starts, and its cost")
        for path, start, cost, leaks in asyncio.run(run()):
            print(f"  {path:26} {start:>8,} tokens  ${cost:.4f}  {'mentions ' + ', '.join(leaks) if leaks else ''}")


if __name__ == "__main__":
    sys.exit(main())
