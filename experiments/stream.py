import time
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
start = time.perf_counter()
first = None

with client.messages.stream(
    model="claude-haiku-4-5",
    max_tokens=300,
    messages=[
        {
            "role": "user",
            "content": "Write one quiz question about HTTP status codes, with four options and the answer.",
        }
    ],
) as stream:
    for text in stream.text_stream:
        if first is None:
            first = time.perf_counter() - start
        print(text, end="", flush=True)
    message = stream.get_final_message()

print(f"\n\nfirst text after {first:.2f} s, whole reply after {time.perf_counter() - start:.2f} s")
print(
    "stop_reason:",
    message.stop_reason,
    "| blocks:",
    len(message.content),
    "| output tokens:",
    message.usage.output_tokens,
)
