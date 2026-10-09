"""The writer agent, four times: each run ends on a different stop condition."""
import sys

from quizforge import agent, usage, writer_tools
from quizforge.client import make_client
from quizforge.config import load_config
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt

cfg = load_config()
prices = usage.load_prices("pricing.toml")
system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
LESSON = sys.argv[1]
ASK = f"Write {cfg.questions} questions for lesson {LESSON}, and save them."


def person(data):
    """The approval step: a person sees questions that passed the checks, and decides."""
    for n, q in enumerate(data.questions, 1):
        print(f"    {n}. {q.scenario[:90]}")
    return input("    Save these questions? [y/n] ").strip().lower() == "y"


RUNS = [("enough room, a person approves", agent.Limits(), person),
        ("a 2-turn limit", agent.Limits(max_turns=2), person),
        ("a 2-cent budget", agent.Limits(max_usd=0.02), person),
        ("a person declines", agent.Limits(), person)]

for name, limits, approve in RUNS:
    print(f"\n{name}:")
    meter = Meter(make_client(), prices, cfg.model)
    result = agent.run(meter, cfg, system, writer_tools.tools(cfg), writer_tools.act(cfg, approve), ASK, limits)
    print(f"  stopped: {result.stopped} after {result.turns} turn(s), {meter.requests} request(s), ${meter.cost:.4f}")
    if result.text:
        print(f"  Claude: {result.text.strip()[:160]}")
