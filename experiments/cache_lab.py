"""Prompt caching, scene by scene, on real requests (Claude Haiku 4.5, one short question each).
Usage: python -m experiments.cache_lab SCENE   (1 none, 2 wrong breakpoint, 3 stable prefix, 4 too small,
5 a changing system prompt, 6 another model). Each row: input, cache write, cache read, output, cost, seconds,
and the miss reason from cache diagnostics when there is one."""
import json
import sys
import time
from datetime import datetime

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.library import load_lesson
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt
from quizforge.sanitize import clean

cfg, client = load_config(), make_client()
prices = usage.load_prices(ROOT / "pricing.toml")
SYSTEM = for_schema(load_prompt(cfg.prompts, cfg.prompt))
CACHE = {"type": "ephemeral"}


def objectives(lesson):
    rows = json.loads((cfg.library / "MANIFEST.json").read_text())["lessons"]
    return next(row["objectives"] for row in rows if row["lesson"] == lesson)


def ask(lesson, n, cached=True, ask_first=False, system=SYSTEM, model=cfg.model, previous=False):
    """One request: the lesson block and the ask block, the breakpoint where `cached` and `ask_first` put it."""
    text = f'<lesson id="{lesson}">\n{clean(load_lesson(cfg.library, lesson))}\n</lesson>'
    lesson_block = {"type": "text", "text": text}
    ask_block = {"type": "text", "text": f"Write 1 question on: {objectives(lesson)[n]}"}
    blocks = [lesson_block, ask_block]
    if cached and ask_first:   # the common mistake: the breakpoint on the block that changes every request
        blocks[1] = {**ask_block, "cache_control": CACHE}
    elif cached:               # the breakpoint on the last block that stays the same
        blocks[0] = {**lesson_block, "cache_control": CACHE}
    extra = {"diagnostics": {"previous_message_id": previous or None}} if previous is not False else {}
    start = time.perf_counter()
    meter = Meter(client, prices, model, log=cfg.usage_log, label=f"cache lab {lesson} #{n + 1}")  # logged and priced
    reply = meter.messages.create(model=model, max_tokens=400, system=system,
                                  messages=[{"role": "user", "content": blocks}], **extra)
    u, why = reply.usage, getattr(reply, "diagnostics", None)
    reason = why.cache_miss_reason.type if why and why.cache_miss_reason else ""
    print(f"{lesson} #{n + 1}  input {u.input_tokens:5,}  write {u.cache_creation_input_tokens or 0:5,}  read "
          f"{u.cache_read_input_tokens or 0:5,}  output {u.output_tokens:3}  ${usage.cost(prices, model, u):.5f}  "
          f"{time.perf_counter() - start:4.1f} s  {reason}")
    return reply.id


scene = sys.argv[1]
if scene == "1":
    for n in range(3):
        ask("L2.4", n, cached=False)
if scene == "2":
    for n in range(3):
        ask("L2.4", n, ask_first=True)
if scene == "3":
    for n in range(3):
        ask("L2.4", n)
if scene == "4":
    for n in range(2):
        ask("L0.1", n)
if scene == "5":
    last = None
    for n in range(3):
        stamped = SYSTEM + f"\n\nRun {n + 1} at {datetime.now():%H:%M:%S}"  # "harmless": to match prompts to traces
        last = ask("L2.4", n, system=stamped, previous=last)
if scene == "6":
    last = ask("L2.4", 0, previous=None)
    ask("L2.4", 0, model="claude-haiku-5-5", previous=last)
