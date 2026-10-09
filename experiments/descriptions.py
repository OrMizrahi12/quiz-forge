import sys

import anthropic
from dotenv import load_dotenv

from quizforge.config import load_config
from quizforge.library import lesson_ids

load_dotenv()
client = anthropic.Anthropic()
cfg = load_config()
style, runs = sys.argv[1], int(sys.argv[2])

DESCRIBE = {
    "vague": "Reads a lesson.",
    "clear": "Returns the full notes of one lesson in the Quiz Forge library, as Markdown. The id is the letter L "
             "and the lesson number, such as L2.3 for lesson 2.3; anything else is not found.",
}[style]
TOOLS = [{"name": "read_lesson", "description": DESCRIBE,
          "input_schema": {"type": "object", "properties": {"lesson_id": {"type": "string"}}, "required": ["lesson_id"]}}]
ASK = "Write one practice question about lesson 3.2 of the course."

right = 0
for run in range(1, runs + 1):
    reply = client.messages.create(model=cfg.model, max_tokens=500, tools=TOOLS,
                                   messages=[{"role": "user", "content": ASK}])
    call = next((block for block in reply.content if block.type == "tool_use"), None)
    if call is None:
        print(f"{style}, run {run}: no tool call ({reply.stop_reason})")
        continue
    ok = call.input.get("lesson_id") in lesson_ids(cfg.library)
    right += ok
    print(f"{style}, run {run}: {call.name} {call.input} -> {'found' if ok else 'not an id in the library'}")
print(f"== {style}: an id the library has {right}/{runs}")
