"""Code graders: everything about an item that code can check, with Quiz Forge's own rules (validate.py).
Usage: python -m evals.graders  (grades every item in evals/golden.jsonl)"""
import json

from pydantic import ValidationError

from quizforge.config import ROOT, load_config
from quizforge.library import load_lesson
from quizforge.sanitize import clean
from quizforge.schema import Question, Questions
from quizforge.validate import problems


def grade(item, library):
    """[(grader, passed, detail)] for one item: the schema first, then each business rule."""
    try:
        question = Question.model_validate(item["item"])
    except ValidationError as error:
        return [("schema", False, error.errors()[0]["type"])]
    found = problems(Questions(questions=[question]), clean(load_lesson(library, item["lesson"])), 1)
    return [
        ("schema", True, ""),
        ("rules", not found, "; ".join(found)),
    ]


def load(name="golden.jsonl"):
    return [json.loads(line) for line in (ROOT / "evals" / name).read_text().splitlines() if line.strip()]


if __name__ == "__main__":
    library, items = load_config().library, load()
    passed = [item for item in items if all(ok for _, ok, _ in grade(item, library))]
    for item in items:
        print(f"{item['id']:12} {'pass' if item in passed else 'FAIL'}  label {item['label']}")
    good = sum(item["label"] == "good" for item in passed)
    print(f"\n{len(passed)} of {len(items)} pass the code graders; their labels: {good} good, {len(passed) - good} bad")
