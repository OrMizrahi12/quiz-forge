"""The person's checkpoint: nothing reaches bank/approved/ without a yes. One lesson at a time, the person sees the questions,
their citations and the checker's verdicts; y moves them to approved/, n to declined/, anything else leaves them pending."""

import json
from datetime import datetime, timezone

from quizforge import sources


def pending(cfg, lessons=None):
    """The lessons waiting for review, oldest id first; lessons: only these."""
    return [p for p in sorted((cfg.bank / "pending").glob("*.json")) if not lessons or p.stem in lessons]


def pending_ids(cfg):
    return [p.stem for p in pending(cfg)]


def counts(cfg):
    """How many questions each lesson has in bank/pending/ and approved/: {lesson: {"pending": n, "approved": n}}.
    A lesson with questions in bank/declined/ also gets a "declined": n."""
    found = {}
    for folder in ("pending", "approved", "declined"):
        for path in (cfg.bank / folder).glob("*.json"):
            found.setdefault(path.stem, {"pending": 0, "approved": 0})[folder] = len(
                json.loads(path.read_text())["questions"]
            )
    return dict(sorted(found.items()))


def verdict(item, n):
    """The checker's verdict on question n, without the 'Question n: ' prefix; 'not checked' if there is none."""
    lines = item.get("verdicts") or []
    return lines[n - 1].split(": ", 1)[1] if n <= len(lines) and ": " in lines[n - 1] else "not checked"


def show(item, out=print):
    out(
        f"{item['lesson']}: {len(item['questions'])} question(s), {item['model']}, prompt {item['prompt']}, "
        f"job stopped: {item.get('stopped', 'unknown')}"
    )
    for n, q in enumerate(item["questions"], 1):
        out(f"\n{n}. {q['scenario']}")
        for key in "abcd":
            out(f"   {key.upper()}) {q[key]}")
        out(f"   Answer: {q['answer']}. {q['why']}")
        out(f'   Quote ({q.get("section") or item["lesson"]}): "{q["quote"]}"')
        out(f"   Checker: {verdict(item, n)}")
    lines = item.get("verdicts") or []
    if len(lines) < len(item["questions"]) or not all(sources.supported(line) for line in lines):
        out("\n   warning: the checker did not support every question")


def move(cfg, path, folder):
    """The lesson's questions join bank/<folder>/<lesson>.json, each with its verdict and the date; the pending file goes."""
    item, target = json.loads(path.read_text()), cfg.bank / folder / path.name
    kept = json.loads(target.read_text()) if target.exists() else {"lesson": item["lesson"], "questions": []}
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    kept["questions"] += [
        {**q, "verdict": verdict(item, n), "model": item["model"], "prompt": item["prompt"], folder: stamp}
        for n, q in enumerate(item["questions"], 1)
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(kept, indent=2) + "\n")
    path.unlink()
    return target


def review(cfg, lessons=None, ask=input, out=print):
    """Ask a person about each pending lesson. Returns {lesson: approved | declined | pending}."""
    decided = {}
    for path in pending(cfg, lessons):
        item = json.loads(path.read_text())
        show(item, out)
        try:
            answer = (
                ask(f"\nApprove these {len(item['questions'])} question(s) for {item['lesson']}? [y/n] ")
                .strip()
                .lower()
            )
        except EOFError:  # no one there to answer: nothing is decided
            answer = None
        if answer in ("y", "yes"):
            decided[item["lesson"]] = "approved"
        elif answer in ("n", "no"):
            decided[item["lesson"]] = "declined"
        else:
            decided[item["lesson"]] = "pending"
            out(f"{item['lesson']}: no decision, left in bank/pending/")
            if answer is None:
                break
            continue
        moved = move(cfg, path, decided[item["lesson"]])
        out(f"{item['lesson']}: {decided[item['lesson']]}, moved to bank/{moved.parent.name}/{moved.name}")
    return decided
