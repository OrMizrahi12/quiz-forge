import json
import re
import sys

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from quizforge.schema import ListQuestions, Questions

load_dotenv()
client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5-20251001"
RULES = open("prompts/item_writer/system.md").read()
RULES = re.sub(r"<format>.*</format>", "", RULES, flags=re.S)
lesson = open("library/ccao-f/v1/L2.1.md").read()
ASK = f'<lesson id="L2.1">\n{lesson}\n</lesson>\n\nWrite 2 questions.'
SCHEMA = anthropic.transform_schema(Questions)
TOOL = {"name": "save_questions", "description": "Save the questions to the Quiz Forge bank.",
        "strict": True, "input_schema": SCHEMA}


def send(mode):
    if mode == "ask":
        prompt = ASK + "\nReply with only JSON that matches this schema:\n"
        prompt += json.dumps(SCHEMA)
        return client.messages.create(model=MODEL, max_tokens=2000, system=RULES,
                                      messages=[{"role": "user", "content": prompt}])
    if mode in ("list", "fixed"):
        shape = ListQuestions if mode == "list" else Questions
        return client.messages.parse(model=MODEL, max_tokens=2000, system=RULES,
                                     messages=[{"role": "user", "content": ASK}],
                                     output_format=shape)
    return client.messages.create(model=MODEL, max_tokens=2000, system=RULES, tools=[TOOL],
                                  tool_choice={"type": "tool", "name": "save_questions"},
                                  messages=[{"role": "user", "content": ASK}])


def read(mode, message):
    if mode == "ask":
        return Questions.model_validate_json(message.content[0].text)
    if mode == "tool":
        return Questions.model_validate(message.content[0].input)
    return message.parsed_output


def shape(question):
    if hasattr(question, "options"):
        return len(question.options), sum(option.correct for option in question.options)
    return 4, 1   # four required fields and one answer letter: nothing else fits the schema


runs, modes = int(sys.argv[1]), sys.argv[2].split(",")
for mode in modes:
    valid = rules = tokens = 0
    for run in range(1, runs + 1):
        message = send(mode)
        tokens += message.usage.input_tokens
        if mode == "ask":
            open(f"runs/as_data-ask-{run}.txt", "w").write(message.content[0].text)
        try:
            data = read(mode, message)
        except ValidationError as error:
            print(f"{mode}, run {run}: INVALID, {error.errors()[0]['type']}")
            continue
        bad = [shape(q) for q in data.questions if shape(q) != (4, 1)]
        valid, rules = valid + 1, rules + (not bad)
        open(f"runs/as_data-{mode}-{run}.json", "w").write(data.model_dump_json(indent=2))
        result = "4 options, 1 correct"
        if bad:
            result = f"FAIL: {bad[0][0]} options, {bad[0][1]} correct"
        print(f"{mode}, run {run}: valid, {result}")
    print(f"== {mode}: valid {valid}/{runs}, 4 options and 1 correct {rules}/{runs}, "
          f"input tokens {tokens // runs} per call\n")
