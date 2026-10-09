import time

import anthropic
from dotenv import load_dotenv

from quizforge.tools import TOOLS, cfg, run_all

load_dotenv()
client = anthropic.Anthropic()

ASK = "Check every source that lesson L3.2 cites, and give me a short report."
messages = [{"role": "user", "content": ASK}]
for turn in range(1, 9):   # the turn limit: a loop that never ends is a bill that never ends
    reply = client.messages.create(model=cfg.model, max_tokens=1500, tools=TOOLS,
                                   messages=messages)
    calls = [block for block in reply.content if block.type == "tool_use"]
    print(f"request {turn}: {reply.stop_reason}, {len(calls)} tool calls")
    if reply.stop_reason != "tool_use":
        break
    started = time.perf_counter()
    results = run_all(calls)
    print(f"  {len(results)} results in one user message, {time.perf_counter() - started:.1f} s")
    messages += [{"role": "assistant", "content": reply.content},
                 {"role": "user", "content": results}]
report = next((block.text for block in reply.content if block.type == "text"), "")
open("runs/sources.md", "w").write(report + "\n")
print("report -> runs/sources.md")
