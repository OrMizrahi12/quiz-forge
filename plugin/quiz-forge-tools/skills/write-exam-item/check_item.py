"""Checks a pending lesson file with Quiz Forge's own rules: the schema, validate.problems, the quote's section, and
item memory (no repeated situation). Prints ok, or one line per problem."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from quizforge import memory
from quizforge.config import load_config
from quizforge.library import load_lesson
from quizforge.sanitize import clean
from quizforge.schema import Questions
from quizforge.search import section_of
from quizforge.validate import problems

cfg = load_config()
path = Path(sys.argv[1])
item = json.loads(path.read_text())
data = Questions.model_validate({"questions": item["questions"]})
found = problems(data, clean(load_lesson(cfg.library, item["lesson"])), len(data.questions))
for n, q in enumerate(item["questions"], 1):
    where = section_of(cfg.library, item["lesson"], q["quote"])
    if where and q.get("section") != where:
        found.append(f"question {n}: section should be {where}")
found += memory.repeats([q.scenario for q in data.questions], memory.known_stems(cfg.bank, skip=path), cfg.similar)
print("\n".join(found) or f"ok: {len(data.questions)} question(s) pass the checks")
sys.exit(1 if found else 0)
