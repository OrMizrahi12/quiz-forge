import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

PROMPT = "In one paragraph, explain how a language model writes a reply."

with client.messages.stream(
    model="claude-haiku-4-5",
    max_tokens=20,
    messages=[{"role": "user", "content": PROMPT}],
) as stream:
    for text in stream.text_stream:
        print(text, end="|", flush=True)
    message = stream.get_final_message()

print()
print("stop_reason:", message.stop_reason)
print("usage:", message.usage.input_tokens, "in,", message.usage.output_tokens, "out")
