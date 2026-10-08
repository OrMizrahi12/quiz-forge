import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

for model in client.models.list(limit=20):
    print(f"{model.id:28} {str(model.line):7} {model.max_input_tokens:>9,} in {model.max_tokens:>8,} out")

alias = client.models.retrieve("claude-haiku-4-5")
print("\nclaude-haiku-4-5 is", alias.id, "|", alias.lifecycle)

message = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=20,
    messages=[{"role": "user", "content": "Say hi."}],
)
print("the reply came from:", message.model)
