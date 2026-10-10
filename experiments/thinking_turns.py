import anthropic
from dotenv import load_dotenv

from quizforge.tools import TOOLS, cfg, run_all

load_dotenv()
client = anthropic.Anthropic()
QUESTION = "Which lesson in the library is about hallucinations? List its three objectives."
ask = {"role": "user", "content": QUESTION}
thinking = {"type": "enabled", "budget_tokens": 1024}

first = client.messages.create(model=cfg.model, max_tokens=3000, thinking=thinking, tools=TOOLS, messages=[ask])
print(f"first reply: {[block.type for block in first.content]}")
results = run_all([block for block in first.content if block.type == "tool_use"])


def unsigned(block):
    """A thinking block rebuilt by hand: the text kept, the signature lost."""
    return {"type": "thinking", "thinking": block.thinking} if block.type == "thinking" else block


ways = {
    "sent back as received": first.content,
    "thinking dropped": [block for block in first.content if block.type != "thinking"],
    "thinking without its signature": [unsigned(block) for block in first.content],
}
for name, content in ways.items():
    turn = [ask, {"role": "assistant", "content": content}, {"role": "user", "content": results}]
    try:
        reply = client.messages.create(model=cfg.model, max_tokens=3000, thinking=thinking, tools=TOOLS, messages=turn)
        print(f"{name}: {reply.stop_reason}, {reply.usage.input_tokens} in")
    except anthropic.BadRequestError as error:
        print(f"{name}: 400 {error.body['error']['message']}")
