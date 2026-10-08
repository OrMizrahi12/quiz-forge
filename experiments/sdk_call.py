import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=100,
    system="You write quiz questions for developers.",
    messages=[
        {"role": "user", "content": "Write one quiz question about HTTP status codes. Reply with the question only."}
    ],
)
print(message.content[0].text)
print("stop_reason:", message.stop_reason)
print("usage:", message.usage.input_tokens, "in,", message.usage.output_tokens, "out")
print("request id:", message._request_id)
print("retries:", client.max_retries)

try:
    client.messages.create(
        model="claude-haiku-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": "Hi"}],
    )
except anthropic.NotFoundError as error:
    print("404:", error.body["error"]["message"])
