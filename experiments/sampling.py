import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

PROMPT = "Write one quiz question about tokens. Reply with the question only."


def ask(model, **sampling):
    message = client.messages.create(
        model=model,
        max_tokens=60,
        messages=[{"role": "user", "content": PROMPT}],
        extra_body=sampling,
    )
    return message.content[0].text


print("Haiku 4.5, default temperature:")
for _ in range(5):
    print(" ", ask("claude-haiku-4-5"))

print("Haiku 4.5, temperature 0:")
for _ in range(5):
    print(" ", ask("claude-haiku-4-5", temperature=0))

print("Haiku 5.5, temperature 0:")
try:
    print(" ", ask("claude-haiku-5-5", temperature=0))
except anthropic.BadRequestError as error:
    print("  400:", error.body["error"]["message"])
