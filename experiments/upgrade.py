import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
ASK = [{"role": "user", "content": "Write one quiz question about DNS. Question only."}]
REQUESTS = {   # two Haiku 4.5 habits, then the migrated request
    "temperature": dict(messages=ASK, extra_body={"temperature": 0.2}),
    "prefill": dict(messages=ASK + [{"role": "assistant", "content": "Question:"}]),
    "migrated": dict(messages=ASK),
}

for model in ["claude-haiku-4-5-20251001", "claude-haiku-5-5", "claude-3-haiku-20240307"]:
    print(f"\n{model}")
    for name, request in REQUESTS.items():
        try:
            message = client.messages.create(model=model, max_tokens=300, **request)
            text = next(block.text for block in message.content if block.type == "text")
            print(f"  {name:12} OK   {' '.join(text.split())[:70]}")
        except anthropic.APIStatusError as error:
            print(f"  {name:12} {error.status_code}  {error.body['error']['message']}")
