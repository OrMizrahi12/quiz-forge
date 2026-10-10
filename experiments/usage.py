import json
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
PRICES = {  # dollars per million tokens, input and output (pricing page, 2026-10-08)
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
WRITE, READ = 1.25, 0.10  # cache writes and cache reads, times the input price
LIMIT = 0.01  # refuse any single request that could cost more than a cent


def cost(model, usage):
    price_in, price_out = PRICES[model]
    tokens_in = (
        usage.input_tokens
        + WRITE * (usage.cache_creation_input_tokens or 0)
        + READ * (usage.cache_read_input_tokens or 0)
    )
    return (tokens_in * price_in + usage.output_tokens * price_out) / 1_000_000


def call(label, model, max_tokens, system, messages, **extra):
    price_in, price_out = PRICES[model]
    counted = client.messages.count_tokens(model=model, system=system, messages=messages).input_tokens
    most = (counted * price_in + max_tokens * price_out) / 1_000_000
    if most > LIMIT:
        raise SystemExit(f"{label}: could cost ${most:.4f}, over the ${LIMIT} limit")
    message = client.messages.create(model=model, max_tokens=max_tokens, system=system, messages=messages, **extra)
    usage = message.usage
    row = {
        "label": label,
        "model": model,
        "counted": counted,
        "input": usage.input_tokens,
        "write": usage.cache_creation_input_tokens or 0,
        "read": usage.cache_read_input_tokens or 0,
        "output": usage.output_tokens,
        "cost": cost(model, usage),
    }
    with open("runs/usage.jsonl", "a") as log:
        log.write(json.dumps(row) + "\n")
    print(
        f"{label:13}{counted:5} counted {row['input']:5} in {row['write']:5} write "
        f"{row['read']:5} read {row['output']:4} out ${row['cost']:.5f}"
    )
    return message
