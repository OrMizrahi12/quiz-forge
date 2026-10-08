import glob
import sys

from quizforge.schema import Questions
from quizforge.validate import words

version = sys.argv[1]
for path in sorted(glob.glob(f"runs/{version}-*.json")):
    lesson = words(open(f"library/ccao-f/v1/{path.split('-')[1]}.md").read())
    data = Questions.model_validate_json(open(path).read())
    for n, q in enumerate(data.questions, 1):
        if words(q.quote) not in lesson:
            print(f"{path}, question {n}:\n  {q.quote}\n")
