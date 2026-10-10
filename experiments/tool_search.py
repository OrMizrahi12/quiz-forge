import anthropic
from dotenv import load_dotenv

from quizforge.tools import TOOLS, cfg

load_dotenv()
client = anthropic.Anthropic()
# Stand-ins: 36 admin tools that only have definitions, to see what a large tool set costs.
VERBS = ["export", "import", "archive", "grade", "schedule", "translate"]
THINGS = ["quiz", "lesson", "question", "student", "report", "course"]
STAND_INS = [
    {
        "name": f"{verb}_{thing}",
        "description": f"{verb.capitalize()}s one {thing} in the Quiz Forge admin system.",
        "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    }
    for verb in VERBS
    for thing in THINGS
]
SEARCH = {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"}
ask = [{"role": "user", "content": "Which lesson is about hallucinations? List its objectives."}]


def show(name, tools):
    reply = client.messages.create(model=cfg.model, max_tokens=800, tools=tools, messages=ask)
    print(f"{name}: {reply.usage.input_tokens} in")
    for block in reply.content:
        if block.type in ("server_tool_use", "tool_use"):
            print(f"  {block.type} {block.name} {block.input}")


show("39 tools, all loaded", TOOLS + STAND_INS)
show("3 tools loaded, 36 deferred", [SEARCH] + TOOLS + [dict(t, defer_loading=True) for t in STAND_INS])
