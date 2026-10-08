import time
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
HARD = ("A quiz has 7 questions, each with options A to D. The answer key must use every letter at least once, "
        "never repeat a letter on two questions in a row, and start and end with the same letter. "
        "How many answer keys are possible? Reply with the number only.")
REQUESTS = {   # the older wording, then today's controls
    "budget 2000": dict(thinking={"type": "enabled", "budget_tokens": 2000}),
    "adaptive": dict(thinking={"type": "adaptive"}),
    "effort low": dict(output_config={"effort": "low"}),
}

for model in ["claude-haiku-4-5-20251001", "claude-haiku-5-5"]:
    print(f"\n{model}")
    for name, request in REQUESTS.items():
        try:
            start = time.perf_counter()
            message = client.messages.create(model=model, max_tokens=8000,
                                             messages=[{"role": "user", "content": HARD}], **request)
            seconds = time.perf_counter() - start
            answer = next(block.text for block in message.content if block.type == "text").split()[-1].strip("*.")
            print(f"  {name:12} OK   {seconds:5.2f} s  {message.usage.output_tokens_details.thinking_tokens:5} thinking  answer {answer}")
        except anthropic.APIStatusError as error:
            print(f"  {name:12} {error.status_code}  {error.body['error']['message']}")
