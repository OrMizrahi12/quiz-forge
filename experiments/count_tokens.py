import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

WINDOWS = {"claude-haiku-4-5": 200_000, "claude-haiku-5-5": 1_000_000}

text = open(sys.argv[1]).read()
print(f"{len(text):,} characters")

for model, window in WINDOWS.items():
    count = client.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}],
    )
    tokens = count.input_tokens
    print(f"{model}: {tokens:,} tokens,",
          f"{len(text) / tokens:.1f} characters each,",
          f"{tokens / window:.1%} of the window")
