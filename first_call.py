import anthropic
from dotenv import load_dotenv

load_dotenv()  # reads .env into the environment
client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY

message = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "What is an API key? One sentence."}],
)

print(message.content[0].text)
print("stop_reason:", message.stop_reason)
print("usage:", message.usage.input_tokens, "in,", message.usage.output_tokens, "out")
print("id:", message.id)
