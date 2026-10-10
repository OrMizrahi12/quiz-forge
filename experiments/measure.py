import asyncio
import re
import sys
from collections import Counter

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from quizforge.repair import FORMAT
from quizforge.sanitize import clean
from quizforge.schema import Questions
from quizforge.validate import problems

load_dotenv()
client = anthropic.AsyncAnthropic()
MODEL = "claude-haiku-4-5-20251001"
LESSONS = ["L1.3", "L2.1", "L3.2"]
limit = asyncio.Semaphore(6)
version, runs = sys.argv[1], int(sys.argv[2])
system = open(f"prompts/item_writer/{version}.md").read()
system = re.sub(r"<format>.*</format>", "", system, flags=re.S)


async def one(lesson_id, run):
    lesson = clean(open(f"library/ccao-f/v1/{lesson_id}.md").read())
    ask = f'<lesson id="{lesson_id}">\n{lesson}\n</lesson>\n\nWrite 2 questions.'
    async with limit:
        message = await client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": ask}],
            output_config=FORMAT,
        )
    text = message.content[0].text
    open(f"runs/{version}-{lesson_id}-{run}.json", "w").write(text)
    try:
        return problems(Questions.model_validate_json(text), lesson, 2)
    except ValidationError as error:
        return [f"not valid against the schema: {error.errors()[0]['type']}"]


async def main():
    jobs = [(lesson_id, run) for lesson_id in LESSONS for run in range(1, runs + 1)]
    results = await asyncio.gather(*(one(*job) for job in jobs))
    kinds = Counter()
    for (lesson_id, run), found in zip(jobs, results):
        print(f"{lesson_id} run {run}: " + ("; ".join(found) or "pass"))
        kinds.update(re.sub(r"^question \d+: ", "", problem) for problem in found)
    passed = sum(not found for found in results)
    summary = f"{version}: pass {passed}/{len(jobs)}"
    summary += "".join(f"; {kind} {n}" for kind, n in kinds.most_common())
    print("== " + summary)
    open("runs/measure.log", "a").write(summary + "\n")


asyncio.run(main())
