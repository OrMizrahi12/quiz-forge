import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
messages = []

for turn in [
    "Write one quiz question about HTTP status codes. Reply with the question only, no options.",
    "Make it harder. Same format.",
    "What was your first question? Quote it.",
]:
    messages.append({"role": "user", "content": turn})
    reply = client.messages.create(model="claude-haiku-4-5", max_tokens=200, messages=messages)
    text = reply.content[0].text
    messages.append({"role": "assistant", "content": text})
    print(f"> {turn}\n{text}\n  [{reply.usage.input_tokens} in, {reply.usage.output_tokens} out]\n")

fresh = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=60,
    messages=[{"role": "user", "content": "What was your first question? Quote it."}],
)
print("Fresh call, no history:", fresh.content[0].text)
