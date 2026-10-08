import json
from pathlib import Path

from quizforge.validate import loads_lenient, problems

lesson = open("library/ccao-f/v1/L2.1.md").read()
for mode, ext in (("ask", "txt"), ("fixed", "json"), ("tool", "json")):
    passed = 0
    files = sorted(Path("runs").glob(f"as_data-{mode}-*.{ext}"))
    for path in files:
        text = path.read_text()
        try:
            json.loads(text)
            strict = "parses"
        except json.JSONDecodeError:
            strict = "fails"
        found = problems(loads_lenient(text), lesson, 2)
        passed += not found
        more = f" (+{len(found) - 1} more)" if len(found) > 1 else ""
        rules = found[0] + more if found else "pass"
        print(f"{path.name}: json.loads {strict}; {rules}")
    print(f"== {mode}: rules pass {passed}/{len(files)}\n")
