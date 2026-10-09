"""The same job three ways: one agent writes questions for four lessons in one context; one clean-context agent per lesson, in
sequence; or a supervisor hands each lesson to a subagent with a clean context, in parallel. Requests, input tokens, cost,
wall time, lessons saved."""
import sys
import time

from quizforge import agent, team, usage, writer_tools
from quizforge.client import make_client
from quizforge.config import load_config
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt

cfg = load_config()
prices = usage.load_prices("pricing.toml")
system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
LESSONS = sys.argv[1:]
ASK = f"Write {cfg.questions} questions for each of these lessons: {', '.join(LESSONS)}. Save each lesson's questions."
saved = []


def approve(data):
    """No person here: every save that passes the checks goes through, and is counted."""
    saved.append(data)
    return True


def show(name, meters, seconds):
    print(f"{name:12} {sum(m.requests for m in meters):2} requests, {sum(m.tokens_in for m in meters):7,} input tokens, "
          f"${sum(m.cost for m in meters):.4f}, {seconds:5.1f} s, {len(saved)} of {len(LESSONS)} saved")


start, meter = time.perf_counter(), Meter(make_client(), prices, cfg.model)
one = agent.run(meter, cfg, system, writer_tools.tools(cfg), writer_tools.act(cfg, approve), ASK,
                agent.Limits(max_turns=30, max_usd=0.60), out=lambda line: None)
show("one agent", [meter], time.perf_counter() - start)
print(f"{'':12} stopped: {one.stopped}, peak input {one.peak:,}")

saved.clear()
start, line = time.perf_counter(), []
for lesson in LESSONS:   # our code writes each brief, and runs them one after another
    line.append(Meter(make_client(), prices, cfg.model))
    team.subagent(line[-1], cfg, system, approve, f"Write {cfg.questions} questions for lesson {lesson}, and save them.",
                  agent.Limits(max_turns=8, max_usd=0.08))
show("in sequence", line, time.perf_counter() - start)

saved.clear()
made = []
def meters():
    made.append(Meter(make_client(), prices, cfg.model))
    return made[-1]
start = time.perf_counter()
lead, reports, summary = team.supervise(meters, cfg, system, approve, ASK)
show("supervisor", made, time.perf_counter() - start)
print(f"{'':12} the supervisor: {lead.requests} requests, {lead.tokens_in:,} input tokens")
for lesson, m, report in reports:
    print(f"{'':12} {lesson}: {m.requests} requests, {m.tokens_in:,} in; {' '.join(report.split())[:60]}")
