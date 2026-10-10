import re
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"
SYSTEM = "You write practice exam questions from course lesson notes. Use only facts stated in the lesson."
LESSON = "L2.1"
lesson = open(f"library/ccao-f/v1/{LESSON}.md").read()
# the lesson as plain text: no Markdown emphasis, single spaces, straight apostrophes, lower case
plain = " ".join(re.sub(r"[*`]", "", lesson).replace("’", "'").split()).lower()


def render(version):
    text = open(f"prompts/item_writer/{version}.md").read()
    text = text.replace("{{lesson_id}}", LESSON).replace("{{questions}}", "2")
    return text.replace("{{lesson}}", lesson)


def checks(reply):
    support = [
        line for line in reply.splitlines() if re.match(r"\W*(Explanation|Quote|Why)", line)
    ]  # lines that cite the lesson
    quotes = [q for line in support for q in re.findall(r'["“]([^"”]{20,})["”]', line)]
    found = [" ".join(q.replace("’", "'").split()).lower() in plain for q in quotes]
    return {
        "plain text": not re.search(r"^#|\*\*", reply, re.M),
        "8 options": len(re.findall(r"^\W*[A-D]\)", reply, re.M)) == 8,
        "no all/none": not re.search(r"(all|none) of the above", reply, re.I),
        "exact quotes": bool(found) and all(found),
    }


version, runs = sys.argv[1], int(sys.argv[2])
totals, answers = {}, []
for run in range(1, runs + 1):
    message = client.messages.create(
        model=MODEL, max_tokens=1500, system=SYSTEM, messages=[{"role": "user", "content": render(version)}]
    )
    reply = message.content[0].text
    result = checks(reply)
    answers += re.findall(r"Answer:\W*([A-D])", reply)
    for name, ok in result.items():
        totals[name] = totals.get(name, 0) + ok
    marks = [f"{name} {'PASS' if ok else 'FAIL'}" for name, ok in result.items()]
    print(f"{version} run {run}  " + "  ".join(marks))
open(f"runs/{version}-reply.md", "w").write(reply)  # the last reply, to read
print(f"\n{version}: " + ", ".join(f"{name} {n}/{runs}" for name, n in totals.items()))
print("answers: " + " ".join(answers))
