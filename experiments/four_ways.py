"""One small job, four ways to build the agent: our own loop, the Tool Runner, the Agent SDK, and Managed Agents.
Who writes the loop, who supplies the tools, where it runs; and what each one cost."""
import asyncio
import logging
import time
from types import SimpleNamespace

from anthropic import beta_tool
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, ToolUseBlock, query

from quizforge import agent, tools, usage
from quizforge.client import make_client
from quizforge.config import load_config
from quizforge.meter import Meter
from quizforge.validate import words

logging.getLogger("asyncio").setLevel(logging.ERROR)   # quiets a harmless note when the SDK's Claude Code process exits
cfg = load_config()
prices = usage.load_prices("pricing.toml")
SYSTEM = "You answer questions about the Quiz Forge course library: one Markdown file of notes per lesson."
ASK = ("Which model tier does lesson L1.3 tell you to start with? Answer in one sentence, then quote the lesson's "
       "sentence word for word.")
EXPECTED = "Start with the smallest tier that can clearly do the job"


def show(name, where, seconds, calls, cost, answer):
    ok = words(EXPECTED) in words(answer)
    if not ok:
        print(" ".join(answer.split())[:300])
    print(f"{name:14} {where:25} {calls} tool call(s), ${cost:.4f}, {seconds:5.1f} s, {'right' if ok else 'WRONG'} quote")


# 1. Our own loop (L4.2): we write the loop, the tool, and every stop.
start, meter = time.perf_counter(), Meter(make_client(), prices, cfg.model)
read = [t for t in tools.TOOLS if t["name"] == "read_lesson"]
one = agent.run(meter, cfg, SYSTEM, read, lambda call: (tools.read_lesson(**call.input), False), ASK,
                agent.Limits(max_turns=4, max_usd=0.05), out=lambda line: None)
show("our loop", "our process", time.perf_counter() - start, len(one.calls), meter.cost, one.text)


# 2. The Tool Runner (L3.3): we write the tool; the SDK runs the loop.
@beta_tool
def read_lesson(lesson_id: str) -> str:
    """Returns the full notes of one lesson, as Markdown.

    Args:
        lesson_id: The lesson's id, such as L1.3.
    """
    return tools.read_lesson(lesson_id)


start, cost, calls = time.perf_counter(), 0.0, 0
runner = make_client().beta.messages.tool_runner(model=cfg.model, max_tokens=cfg.max_tokens, max_iterations=4, system=SYSTEM,
                                                 tools=[read_lesson], messages=[{"role": "user", "content": ASK}])
for reply in runner:
    calls += sum(block.type == "tool_use" for block in reply.content)
    cost += usage.cost(prices, cfg.model, reply.usage)
text = "".join(block.text for block in reply.content if block.type == "text")
show("Tool Runner", "our process", time.perf_counter() - start, calls, cost, text)


# 3. The Agent SDK: Claude Code's loop and its built-in tools, in our process, on our files.
async def sdk():
    options = ClaudeAgentOptions(model=cfg.model, system_prompt=SYSTEM, cwd=str(cfg.library), tools=["Read", "Grep", "Glob"],
                                 allowed_tools=["Read", "Grep", "Glob"], setting_sources=[], max_turns=6, max_budget_usd=0.10,
                                 stderr=lambda line: None)
    messages = [message async for message in query(prompt=ASK + " The lessons are the .md files in this folder.", options=options)]
    calls = sum(isinstance(block, ToolUseBlock) for m in messages if isinstance(m, AssistantMessage) for block in m.content)
    return next(message for message in messages if isinstance(message, ResultMessage)), calls

start = time.perf_counter()
result, calls = asyncio.run(sdk())
show("Agent SDK", "our process, Claude Code", time.perf_counter() - start, calls, result.total_cost_usd or 0.0,
     result.result or "")


# 4. Managed Agents: Anthropic hosts the loop, the tools and the sandbox; our lesson goes up as a file.
client = make_client()
start = time.perf_counter()
lesson = client.beta.files.upload(file=cfg.library / "L1.3.md")
worker = client.beta.agents.create(name="quiz-forge-reader", model=cfg.model, system=SYSTEM,
                                   tools=[{"type": "agent_toolset_20260401"}])
place = client.beta.environments.create(name="quiz-forge-reader", config={"type": "cloud", "networking": {"type": "limited"}})
session = client.beta.sessions.create(agent=worker.id, environment_id=place.id, title="L4.7 four ways",
                                      resources=[{"type": "file", "file_id": lesson.id, "mount_path": "/library/L1.3.md"}],
                                      budget={"type": "limit", "max_list_cost": {"amount": "10", "currency": "USD"}})
try:
    text, steps = "", 0
    with client.beta.sessions.events.stream(session.id) as stream:
        client.beta.sessions.events.send(session.id, events=[{"type": "user.message", "content": [
            {"type": "text", "text": ASK + " The lesson is mounted at /library/L1.3.md."}]}])
        for event in stream:
            if event.type == "agent.message":
                text += "".join(block.text for block in event.content if block.type == "text")
            elif event.type == "agent.tool_use":
                steps += 1
            elif event.type == "session.status_idle":
                break
    seconds, used = time.perf_counter() - start, client.beta.sessions.retrieve(session.id).usage
    tokens = SimpleNamespace(input_tokens=used.input_tokens, output_tokens=used.output_tokens,
                             cache_read_input_tokens=used.cache_read_input_tokens,
                             cache_creation_input_tokens=used.cache_creation.ephemeral_5m_input_tokens)
    cost = usage.cost(prices, cfg.model, tokens) + used.active_seconds / 3600 * 0.08   # tokens, plus $0.08 per hour of running time
    show("Managed Agents", "Anthropic's sandbox", seconds, steps, cost, text)
    print(f"{'':14} the platform's own list cost, in whole cents: {used.list_cost.amount}")
finally:   # nothing is left running, or stored, on Anthropic's side
    client.beta.sessions.delete(session.id)
    client.beta.environments.delete(place.id)
    client.beta.agents.archive(worker.id)
    client.beta.files.delete(lesson.id)
