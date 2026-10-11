"""Quiz Forge's own import graph, as levels: level 0 imports no other quizforge module; each level imports only
from the levels before it. A port or a large refactor moves level by level. Usage: python -m experiments.depmap"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "quizforge"
deps = {}
for path in sorted(ROOT.rglob("*.py")):
    name = ".".join(path.relative_to(ROOT.parent).with_suffix("").parts).removesuffix(".__init__")
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("quizforge"):
            found |= {f"{node.module}.{a.name}" for a in node.names} | {node.module}
        elif isinstance(node, ast.Import):
            found |= {a.name for a in node.names if a.name.startswith("quizforge")}
    deps[name] = found
for name, found in deps.items():
    deps[name] = {d for d in found if d in deps and d != name}
level, placed = 0, set()
while len(placed) < len(deps):
    ready = sorted(n for n in deps if n not in placed and deps[n] <= placed)
    if not ready:
        print("cycle:", sorted(set(deps) - placed))
        break
    print(f"level {level}: {', '.join(n.removeprefix('quizforge.') for n in ready)}")
    placed |= set(ready)
    level += 1
