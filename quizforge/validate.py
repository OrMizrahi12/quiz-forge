import json
import re

from quizforge.schema import Questions


def loads_lenient(text):
    """Defensive parse: keep only the JSON object, whatever is around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object in the reply")
    return Questions.model_validate(json.loads(text[start:end + 1]))


def words(text):
    """The words only, in lower case: a quote is checked word for word, not by punctuation."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def problems(data, lesson, count):
    """The rules the schema can't carry. An empty list means the questions pass."""
    found = []
    if len(data.questions) != count:
        found.append(f"expected {count} questions, got {len(data.questions)}")
    source = words(lesson)
    for n, q in enumerate(data.questions, 1):
        if len({words(x) for x in (q.a, q.b, q.c, q.d)}) < 4:
            found.append(f"question {n}: two options are the same")
        if words(q.quote) not in source:
            found.append(f"question {n}: quote not in the lesson")
        if not q.scenario.rstrip().endswith("?"):
            found.append(f"question {n}: scenario asks no question")
    return found
