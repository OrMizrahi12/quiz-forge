"""One agent, four lessons, three ways to handle its context: keep everything, clear old tool results, or restart."""
import sys

from quizforge import agent, usage, writer_tools
from quizforge.client import make_client
from quizforge.config import load_config
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt

cfg = load_config()
prices = usage.load_prices("pricing.toml")
system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
LESSONS = sys.argv[1:]
LIMITS = agent.Limits(max_turns=30, max_usd=0.60)
CLEAR = {"extra_headers": {"anthropic-beta": "context-management-2025-06-27"},
         "extra_body": {"context_management": {"edits": [{
             "type": "clear_tool_uses_20250919",
             "trigger": {"type": "input_tokens", "value": 10000},    # start clearing above 10k input tokens
             "keep": {"type": "tool_uses", "value": 2},              # keep the two most recent tool uses
             "clear_at_least": {"type": "input_tokens", "value": 3000}}]}}}


def one_task(lessons, extra):
    """One conversation. No person here: every save that passes the checks goes through, and is counted."""
    meter, saved = Meter(make_client(), prices, cfg.model), []

    def approve(data):
        saved.append(data)
        return True

    ask = f"Write {cfg.questions} questions for each of these lessons: {', '.join(lessons)}. Save each lesson's questions."
    result = agent.run(meter, cfg, system, writer_tools.tools(cfg), writer_tools.act(cfg, approve), ask, LIMITS,
                       out=lambda line: None, **extra)
    return meter, result, len(saved)


for name in ("keep everything", "clear old tool results", "restart per lesson"):
    if name == "restart per lesson":
        runs = [one_task([lesson], {}) for lesson in LESSONS]
    else:
        runs = [one_task(LESSONS, CLEAR if name.startswith("clear") else {})]
    requests = sum(m.requests for m, _, _ in runs)
    tokens = sum(m.tokens_in for m, _, _ in runs)
    peak = max(r.peak for _, r, _ in runs)
    cost = sum(m.cost for m, _, _ in runs)
    saved = sum(s for _, _, s in runs)
    reads = sum(r.calls.count("read_lesson") for _, r, _ in runs)
    print(f"{name:23} {requests:2} requests, {tokens:7,} input tokens, peak {peak:6,}, ${cost:.4f}, "
          f"{reads} lesson reads, {saved} of {len(LESSONS)} saved")
    print(f"{'':23} stopped: {', '.join(sorted(set(r.stopped for _, r, _ in runs)))}")
