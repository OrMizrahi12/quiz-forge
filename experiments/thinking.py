import time
from itertools import product
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
EASY = "Write one quiz question about DNS. Question only."
HARD = (
    "A quiz has 7 questions, each with options A to D. The answer key must use every letter at least once, "
    "never repeat a letter on two questions in a row, and start and end with the same letter. "
    "How many answer keys are possible? Reply with the number only."
)
RIGHT = sum(
    1
    for key in product("ABCD", repeat=7)
    if len(set(key)) == 4 and key[0] == key[-1] and all(a != b for a, b in zip(key, key[1:]))
)
print("right answer:", RIGHT)

for name, task, effort, display in [
    ("easy", EASY, "low", "summarized"),
    ("easy", EASY, "high", "summarized"),
    ("hard", HARD, "low", "summarized"),
    ("hard", HARD, "high", "summarized"),
    ("hard", HARD, "high", "omitted"),
]:
    start = time.perf_counter()
    message = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=8000,
        thinking={"type": "adaptive", "display": display},
        output_config={"effort": effort},
        messages=[{"role": "user", "content": task}],
    )
    seconds = time.perf_counter() - start
    usage = message.usage
    text = " ".join(next(block.text for block in message.content if block.type == "text").split())
    shown = sum(len(block.thinking) for block in message.content if block.type == "thinking")
    print(
        f"{name} {effort:4} {display:10} {seconds:5.2f} s  {usage.output_tokens:4} out  "
        f"{usage.output_tokens_details.thinking_tokens:4} thinking  {shown:4} chars shown"
    )
    print(f"    {[block.type for block in message.content]}  {text.strip('*')[:50]}")
