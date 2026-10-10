import anthropic
from dotenv import load_dotenv

from quizforge.tools import TOOLS, cfg, run

load_dotenv()
client = anthropic.Anthropic()
SAVE = {
    "name": "save_question",
    "description": "Appends one finished practice question to the course's question bank "
    "(runs/questions.md). It writes a file, so a person approves each call.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lesson_id": {"type": "string"},
            "question": {"type": "string", "description": "Stem, options A-D, the key and why."},
        },
        "required": ["lesson_id", "question"],
    },
}


def save_question(lesson_id, question):
    open("runs/questions.md", "a").write(f"## {lesson_id}\n\n{question}\n\n")
    return "Saved to runs/questions.md."


def approved(call):
    """A person decides before a tool with side effects runs."""
    print(f"--- {call.name} wants to write:\n{call.input['question']}\n---")
    if input("Approve? [y/n] ").strip().lower() == "y":
        return {"type": "tool_result", "tool_use_id": call.id, "content": save_question(**call.input)}
    return {
        "type": "tool_result",
        "tool_use_id": call.id,
        "is_error": True,
        "content": "The reviewer declined: not saved. Tell the user; don't retry.",
    }


ASK = "Write one practice question about lesson L3.2 and save it to the question bank."
messages = [{"role": "user", "content": ASK}]
for turn in range(1, 9):
    reply = client.messages.create(model=cfg.model, max_tokens=1500, tools=TOOLS + [SAVE], messages=messages)
    calls = [block for block in reply.content if block.type == "tool_use"]
    print(f"request {turn}: {reply.stop_reason}, {[call.name for call in calls]}")
    if reply.stop_reason != "tool_use":
        break
    results = [approved(call) if call.name == "save_question" else run(call) for call in calls]
    messages += [{"role": "assistant", "content": reply.content}, {"role": "user", "content": results}]
print(next((block.text for block in reply.content if block.type == "text"), "")[:300])
