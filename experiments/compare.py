import time
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
TASK = "Write one multiple-choice quiz question about HTTP status codes: four options, mark the answer, one-line explanation."
PRICES = {  # dollars per million tokens, input and output (pricing page, 2026-10-08)
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

for model, (price_in, price_out) in PRICES.items():
    start = time.perf_counter()
    message = client.messages.create(
        model=model,
        max_tokens=1000,
        messages=[{"role": "user", "content": TASK}],
    )
    seconds = time.perf_counter() - start
    usage = message.usage
    cost = (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000
    text = next(block.text for block in message.content if block.type == "text")
    question = next(line for line in text.splitlines() if "?" in line).replace("**", "")
    print(
        f"{model:26} {seconds:5.2f} s {usage.input_tokens:4} in {usage.output_tokens:4} out  ${cost:.5f}  {[b.type for b in message.content]}"
    )
    print("    " + question.removeprefix("Question:").strip()[:100])
