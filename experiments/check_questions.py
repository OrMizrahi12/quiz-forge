import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
client = anthropic.Anthropic()


class Question(BaseModel):
    question: str
    options: list[str]
    answer: int


lesson = open("library/ccao-f/v1/L1.3.md").read()
PROMPT = "Write one multiple-choice quiz question about this lesson, with four options.\n\n" + lesson

for run in range(1, 6):
    message = client.messages.parse(
        model="claude-haiku-5-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": PROMPT}],
        output_format=Question,
    )
    q = message.parsed_output
    ok = len(q.options) == 4 and 0 <= q.answer < 4 and q.question.endswith("?")
    print(run, "PASS" if ok else "FAIL", q.question)
