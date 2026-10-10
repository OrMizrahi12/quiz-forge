"""The same job two ways, measured: two checked questions for one lesson, as a workflow and as an agent."""

import json
import sys

from quizforge import sources, usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_one
from quizforge.library import load_lesson
from quizforge.meter import Meter
from quizforge.prompts import for_schema, load_prompt
from quizforge.sanitize import clean
from quizforge.schema import Question, Questions
from quizforge.tools import TOOLS
from quizforge.validate import problems

cfg = load_config()
prices = usage.load_prices("pricing.toml")
LESSON, RUNS, MAX_TURNS = sys.argv[1], int(sys.argv[2]), 8


SAVE = {
    "name": "save_questions",
    "description": "Saves the finished questions for one lesson. Code checks them first: the number of questions, "
    "four different options, a scenario that ends in a question, and each quote word for word in "
    "the lesson. If a check fails, nothing is saved and the result lists the problems to fix.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lesson_id": {"type": "string"},
            "questions": {"type": "array", "items": Question.model_json_schema()},
        },
        "required": ["lesson_id", "questions"],
    },
}


def save_questions(lesson_id, questions, run):
    data = Questions.model_validate({"questions": questions})
    found = problems(data, clean(load_lesson(cfg.library, lesson_id)), cfg.questions)
    if found:
        raise sources.NotChecked("not saved: " + "; ".join(found) + ". Fix these and call save_questions again.")
    path = cfg.output_dir.parent / "agent" / f"{lesson_id}-run{run}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.model_dump(), indent=2) + "\n")
    return f"saved {len(questions)} questions"


def act(call, run):
    """Our code runs every tool Claude asks for; a failure goes back as is_error, with what to fix."""
    try:
        if call.name == "save_questions":
            return save_questions(**call.input, run=run), False
        if call.name == "check_quote":
            return sources.check_quote(cfg.library, **call.input), False
        if call.name == "read_lesson":
            return clean(load_lesson(cfg.library, call.input["lesson_id"])), False
        return f"no tool named {call.name!r}", True
    except Exception as problem:
        return str(problem), True


def workflow(client, run):
    """Our code sets the path: one request, the checks in code, a repair only if they fail."""
    result = generate_one(cfg, prices, LESSON, client=client, out=lambda line: None)
    return result["status"] == "passed", f"{result['attempts']} attempt(s)"


def agent(client, run):
    """Claude sets the path: it picks the tools and the order, until it stops or hits the turn limit."""
    system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
    tools = [t for t in TOOLS if t["name"] == "read_lesson"] + sources.tools(cfg.library) + [SAVE]
    messages = [{"role": "user", "content": f"Write {cfg.questions} questions for lesson {LESSON}, and save them."}]
    path, saved = [], False
    for turn in range(1, MAX_TURNS + 1):
        reply = client.messages.create(
            model=cfg.model, max_tokens=cfg.max_tokens, system=system, tools=tools, messages=messages
        )
        calls = [block for block in reply.content if block.type == "tool_use"]
        if reply.stop_reason != "tool_use":
            break
        results = []
        for call in calls:
            content, error = act(call, run)
            saved = saved or (call.name == "save_questions" and not error)
            path.append(call.name + (" (error)" if error else ""))
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": error})
        messages += [{"role": "assistant", "content": reply.content}, {"role": "user", "content": results}]
    return saved, ", ".join(path) or "no tools"


runs = {"workflow": [], "agent": []}
for way in (workflow, agent):
    for run in range(1, RUNS + 1):
        meter = Meter(make_client(), prices, cfg.model)
        passed, path = way(meter, run)
        row = {
            "requests": meter.requests,
            "input_tokens": meter.tokens_in,
            "cost": meter.cost,
            "seconds": meter.seconds(),
            "passed": passed,
        }
        runs[way.__name__].append(row)
        print(
            f"{way.__name__:8} run {run}: {row['requests']} request(s), {row['input_tokens']:6,} in, "
            f"${row['cost']:.4f}, {row['seconds']:4.1f} s, {'passed' if passed else 'FAILED'}"
        )
        print(f"         {path}")

mean = {way: {k: round(sum(r[k] for r in rows) / RUNS, 4) for k in rows[0]} for way, rows in runs.items()}
for way, m in mean.items():
    print(
        f"{way:8} per run: {m['requests']:.1f} requests, {m['input_tokens']:7,.0f} in, "
        f"${m['cost']:.4f}, {m['seconds']:4.1f} s, passed {m['passed']:.0%}"
    )
(ROOT / "runs" / "workflow_vs_agent.json").write_text(json.dumps(mean, indent=2) + "\n")
