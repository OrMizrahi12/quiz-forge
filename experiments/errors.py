import sys

import anthropic
from dotenv import load_dotenv

from quizforge.tools import cfg, read_lesson

load_dotenv()
client = anthropic.Anthropic()
style, runs = sys.argv[1], int(sys.argv[2])   # "generic" or "instructive", and how many runs
# Last lesson's vague description, on purpose: Claude's first id will be wrong.
TOOL = {"name": "read_lesson", "description": "Reads a lesson.",
        "input_schema": {"type": "object", "properties": {"lesson_id": {"type": "string"}},
                         "required": ["lesson_id"]}}


def result(call):
    try:
        notes = read_lesson(call.input["lesson_id"])
        return {"type": "tool_result", "tool_use_id": call.id, "content": notes}
    except ValueError as problem:
        message = str(problem) if style == "instructive" else "Error: failed."
        return {"type": "tool_result", "tool_use_id": call.id, "content": message,
                "is_error": True}


recovered = 0
for run in range(1, runs + 1):
    messages = [{"role": "user", "content": "Write one practice question about lesson 3.2."}]
    tried = []
    for turn in range(4):
        reply = client.messages.create(model=cfg.model, max_tokens=600, tools=[TOOL],
                                       messages=messages)
        calls = [block for block in reply.content if block.type == "tool_use"]
        if not calls:
            break
        tried += [call.input.get("lesson_id") for call in calls]
        messages += [{"role": "assistant", "content": reply.content},
                     {"role": "user", "content": [result(call) for call in calls]}]
    recovered += "L3.2" in tried
    print(f"run {run}: ids tried {tried}")
print(f"== {style}: read the right lesson {recovered}/{runs}")
