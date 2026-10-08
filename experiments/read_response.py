import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "Write one quiz question about HTTP status codes, with four options."}],
)
with open("runs/message.json", "w") as f:
    f.write(message.model_dump_json(indent=2))

for block in message.content:
    print(f"[{block.type} block]")
    print(block.text)
print("stop_reason:", message.stop_reason)
print("usage:", message.usage.input_tokens, "in,", message.usage.output_tokens, "out")
print("request id:", message._request_id)
