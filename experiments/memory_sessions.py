"""Three sessions on the same lesson, three ways to remember: nothing, Claude's memory tool, or our own store that the save
check enforces. Does a later session repeat a quote an earlier one used?"""

import json
import shutil
import sys

from quizforge import agent, memory, sources, usage, writer_tools
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt

cfg = load_config()
prices = usage.load_prices("pricing.toml")
system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
LESSON = sys.argv[1]
ASK = (
    f"Write {cfg.questions} new questions for lesson {LESSON}, and save them. Earlier sessions may have saved "
    "questions for it already: don't repeat their quotes."
)
STORE = ROOT / "runs" / "store" / f"{LESSON}.json"


def session(way):
    """One task in a fresh conversation."""
    saved, meter, ask, tools = [], Meter(make_client(), prices, cfg.model), ASK, writer_tools.tools(cfg)
    used = json.loads(STORE.read_text()) if way == "own store" and STORE.exists() else []
    if way == "own store" and used:
        ask += " Quotes already used: " + "; ".join(used)

    def gate(data):
        """The save's last check. With our own store, a repeated quote is refused in code, and Claude must pick another."""
        again = [q.quote for q in data.questions if q.quote in used]
        if again:
            raise sources.NotChecked(f"not saved: already used in an earlier session: {again}. Pick other quotes.")
        saved.append(data)
        return True

    write, store = writer_tools.act(cfg, gate), memory.Memory(ROOT / "runs" / "memory" / LESSON)

    def act(call):
        if call.name != "memory":
            return write(call)
        try:
            return store.run(call.input), False
        except Exception as problem:
            return str(problem), True

    if way == "memory tool":
        tools = tools + [memory.TOOL]
    result = agent.run(
        meter, cfg, system, tools, act, ask, agent.Limits(max_turns=12, max_usd=0.10), out=lambda line: None
    )
    quotes = {q.quote for data in saved for q in data.questions}
    if way == "own store":
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(used + sorted(quotes), indent=1))
    return meter, result, quotes


shutil.rmtree(ROOT / "runs" / "memory" / LESSON, ignore_errors=True)
STORE.unlink(missing_ok=True)
for way in ("no memory", "memory tool", "own store"):
    seen, repeats, cost = set(), 0, 0.0
    for n in range(1, 4):
        meter, result, quotes = session(way)
        repeats += len(quotes & seen)
        seen |= quotes
        cost += meter.cost
        print(
            f"{way:11} session {n}: {result.stopped}, {meter.requests} requests, {meter.tokens_in:6,} in, ${meter.cost:.4f}, "
            f"quotes: {len(quotes)} saved, {repeats} repeated so far"
        )
    print(f"{way:11} 3 sessions: {len(seen)} different quotes, {repeats} repeated, ${cost:.4f}\n")
