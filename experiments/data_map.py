"""Where Quiz Forge's data goes: each place it sends or keeps text, what that place holds, and how many email
addresses, phone numbers and key-shaped strings are in it now. Counts only: a data map must not become one more copy."""

from quizforge.config import ROOT
from quizforge.security.redact import found

PLACES = {
    "library": "lessons: sent to the API as the writer's input",
    "prompts": "our instructions: sent to the API",
    "runs/usage.jsonl": "model, tokens and cost per request",
    "runs/traces": "spans: timings, status codes, request ids",
    "runs/items": "questions written by Claude",
    "runs/agent": "questions saved by the writer agent",
    "runs/memory": "notes the agent keeps between tasks",
    "bank": "questions waiting for, or past, a person's review",
    "runs": "all of runs/, experiments included",
}

for rel, holds in PLACES.items():
    path = ROOT / rel
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    total = {"EMAIL": 0, "PHONE": 0, "KEY": 0}
    for f in files:
        for name, n in found(f.read_text(errors="replace")).items():
            total[name] += n
    counts = "  ".join(f"{name.lower()} {n}" for name, n in total.items())
    print(f"{rel:17} {len(files):4} {'file ' if len(files) == 1 else 'files'}   {counts}   {holds}")
