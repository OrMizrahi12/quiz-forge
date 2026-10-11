"""Label items by hand: the reference labels the judge is measured against. Each label gets a reason.
Usage: python -m evals.label  (labels evals/to_label.jsonl into evals/golden.jsonl, split dev)"""
import json

from evals.graders import load
from quizforge.config import ROOT

for item in load("to_label.jsonl"):
    q = item["item"]
    print(f"\n{item['id']}  ({item['lesson']})\n{q['scenario']}")
    for key in "abcd":
        print(f"  {key.upper()}) {q[key]}")
    print(f'  Key: {q["answer"]}\n  Quote: "{q["quote"]}"')
    label = ""
    while label not in ("good", "bad"):
        label = input("good or bad? ").strip()
    reason = input("reason: ").strip()
    with open(ROOT / "evals/golden.jsonl", "a") as golden:
        golden.write(json.dumps({**item, "label": label, "reason": reason, "split": "dev"}) + "\n")
print("\nlabeled")
