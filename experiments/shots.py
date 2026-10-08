import re
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"
RULES = open("prompts/item_writer/system.md").read()
lesson = open("library/ccao-f/v1/L2.1.md").read()
plain = " ".join(re.sub(r"[*`]", "", lesson).replace("’", "'").split()).lower()


def six_word_runs(text):
    runs = set()
    for line in text.lower().splitlines():
        w = re.findall(r"[a-z0-9']+", line)
        runs |= {" ".join(w[i:i + 6]) for i in range(len(w) - 5)}
    return runs


def ask(examples):
    text = ""
    if examples:
        text = ("<examples>\nThese show the format and the kind of question we want. "
                "Write new scenarios of your own.\n" + "\n".join(examples) + "\n</examples>\n\n")
    return text + f'<lesson id="L2.1">\n{lesson}\n</lesson>\n\nWrite 2 questions.'


runs, counts, source = int(sys.argv[1]), sys.argv[2], sys.argv[3]
pool = re.findall(r"<example>.*?</example>", open(source).read(), re.S)
for k in [int(n) for n in counts.split(",")]:
    examples = pool[:k]
    seen = set().union(*map(six_word_runs, examples))
    exact = copied = tokens = 0
    answers = []
    for run in range(1, runs + 1):
        message = client.messages.create(model=MODEL, max_tokens=1500, system=RULES,
                                         messages=[{"role": "user", "content": ask(examples)}])
        reply = message.content[0].text
        open(f"runs/shots-{k}-{run}.md", "w").write(reply)
        quotes = re.findall(r'^Quote: "(.+)"', reply, re.M)
        ok = bool(quotes) and all(" ".join(q.replace("’", "'").split()).lower() in plain
                                  for q in quotes)
        shared = six_word_runs(reply) & seen
        exact, copied = exact + ok, copied + bool(shared)
        tokens += message.usage.input_tokens
        answers += re.findall(r"^Answer: ([A-D])", reply, re.M)
        print(f"{k} examples, run {run}: exact quotes {'PASS' if ok else 'FAIL'}, "
              f"copied {'YES: ' + min(shared) if shared else 'no'}")
    print(f"== {k} examples: exact quotes {exact}/{runs}, copied {copied}/{runs}, "
          f"input tokens {tokens // runs} per call, answers {' '.join(answers)}\n")
