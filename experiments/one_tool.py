import json

import anthropic
from dotenv import load_dotenv

from quizforge.config import load_config
from quizforge.library import lesson_ids, load_lesson

load_dotenv()
client = anthropic.Anthropic()
cfg = load_config()

READ_LESSON = {
    "name": "read_lesson",
    "description": "Returns the full notes of one lesson from the Quiz Forge library, as Markdown. "
                   "Use it before you write any question about a lesson: the notes are the only source of facts. "
                   "It reads one lesson by its id; it doesn't search, and it can't read anything outside the library.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lesson_id": {"type": "string", "enum": lesson_ids(cfg.library),
                          "description": "The id of one lesson in the library, such as L2.3"},
        },
        "required": ["lesson_id"],
    },
}

messages = [{"role": "user", "content": "Write one multiple-choice practice question about lesson L2.3."}]
first = client.messages.create(model=cfg.model, max_tokens=1000, tools=[READ_LESSON], messages=messages)
print(f"request 1: stop_reason {first.stop_reason}, {first.usage.input_tokens} in, {first.usage.output_tokens} out")
for block in first.content:
    print("  ", json.dumps(block.model_dump(exclude_none=True)))

call = next(block for block in first.content if block.type == "tool_use")
notes = load_lesson(cfg.library, call.input["lesson_id"])   # our code runs the tool; Claude only asked for it
messages += [{"role": "assistant", "content": first.content},
             {"role": "user", "content": [{"type": "tool_result", "tool_use_id": call.id, "content": notes}]}]

second = client.messages.create(model=cfg.model, max_tokens=1000, tools=[READ_LESSON], messages=messages)
print(f"request 2: stop_reason {second.stop_reason}, {second.usage.input_tokens} in, {second.usage.output_tokens} out")
print(second.content[0].text)
