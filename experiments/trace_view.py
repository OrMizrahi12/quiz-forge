"""A terminal view of one trace: the span tree, with the attributes that say where a job broke.
Usage: python -m experiments.trace_view [runs/traces/<file>.jsonl]  (default: the newest trace)"""
import json
import sys
from datetime import datetime
from pathlib import Path

SHOW = ("http.response.status_code", "anthropic.request_id", "gen_ai.response.finish_reasons",
        "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "quizforge.problems", "quizforge.decision")
path = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(Path("runs/traces").glob("*.jsonl"))[-1]
spans = [json.loads(line) for line in path.read_text().splitlines()]
children = {}
for span in spans:
    children.setdefault(span["parent_id"], []).append(span)


def when(span, key):
    return datetime.fromisoformat(span[key].replace("Z", "+00:00")).timestamp()


def show(span, depth=0):
    failed = span["status"]["status_code"] == "ERROR"
    took = when(span, "end_time") - when(span, "start_time")
    facts = "  ".join(str(value) for key, value in span["attributes"].items() if key in SHOW and value != "")
    print(f"{'  ' * depth}{'ERROR' if failed else 'ok   '} {span['name']}  {took:.2f} s  {facts}")
    if failed and span["status"].get("description"):
        print(f"{'  ' * depth}      -> {span['status']['description']}")
    for child in sorted(children.get(span["context"]["span_id"], []), key=lambda s: when(s, "start_time")):
        show(child, depth + 1)


print(path)
for root in children.get(None, []):
    show(root)
