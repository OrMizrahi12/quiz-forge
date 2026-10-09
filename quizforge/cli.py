import argparse
import asyncio
import json
import re

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_many, generate_one
from quizforge.prompts import PromptChanged, digest, load_prompt, lock, locked, versions


def check_model(cfg):
    """The pinned model, checked against the Models API: it must exist and not be retired."""
    info = make_client().models.retrieve(cfg.model)
    print(f"{info.id} | {info.lifecycle} | retires {info.retires_at or 'not scheduled'}")
    if info.lifecycle == "retired":
        raise SystemExit(f"{cfg.model} is retired: pick its replacement, follow the migration guide, rerun your evals")
    if info.lifecycle == "deprecated":
        print(f"warning: {cfg.model} is deprecated; plan the move before {info.retires_at}")
    return info


def measured(folder):
    """The "Measured:" line of each version in CHANGELOG.md, by version."""
    path, found, names = folder / "CHANGELOG.md", {}, []
    for line in (path.read_text().splitlines() if path.exists() else []):
        if line.startswith("## "):
            names = re.findall(r"v\d+", line)
        elif line.startswith("Measured:"):
            found.update({name: line.removeprefix("Measured:").strip() for name in names})
    return found


def show_prompts(cfg):
    hashes, notes = locked(cfg.prompts), measured(cfg.prompts)
    for version in versions(cfg.prompts):
        text = (cfg.prompts / f"{version}.md").read_text()
        state = "unlocked" if version not in hashes else "locked" if hashes[version] == digest(text) else "CHANGED"
        mark = "*" if version == cfg.prompt else " "
        print(f"{mark} {version:4} {state:8} {notes.get(version, '')}")
    print("(* in config.toml)")


def show_items(cfg, lesson_id):
    for folder in (cfg.output_dir, cfg.rejected_dir):
        path = folder / f"{lesson_id}.json"
        if path.exists():
            break
    else:
        raise SystemExit(f"no items for {lesson_id}: run generate --lesson {lesson_id}")
    result = json.loads(path.read_text())
    print(f"{result['lesson']} | prompt {result['prompt']} | {result['status']} after {result['attempts']} attempt(s)")
    for n, q in enumerate(result.get("questions", []), 1):
        print(f"\n{n}. {q['scenario']}")
        for key in "abcd":
            print(f"   {key.upper()}) {q[key]}")
        print(f"   Answer: {q['answer']}. {q['why']}\n   Quote: \"{q['quote']}\"")
    for problem in result.get("problems", []):
        print(f"  problem: {problem}")


def report(result):
    print(f"{result['lesson']}: {result['status']} after {result['attempts']} attempt(s), ${result['cost']:.5f} -> {result['path']}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m quizforge", description="Quiz Forge: checked practice questions from lesson notes")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write checked practice questions for one or more lessons")
    gen.add_argument("--lesson", action="append", required=True, help="a lesson id, e.g. L1.3 (repeat for several)")
    gen.add_argument("--prompt", help="a locked prompt version (default: the one in config.toml)")
    show = sub.add_parser("show", help="print a lesson's saved questions")
    show.add_argument("--lesson", required=True)
    prompts = sub.add_parser("prompts", help="list the prompt versions; --lock freezes one after you measure it")
    prompts.add_argument("--lock", metavar="VERSION")
    sub.add_parser("model", help="check the pinned model against the Models API")
    sub.add_parser("cost", help="total spend from the usage log")
    args = parser.parse_args(argv)

    cfg = load_config()
    prices = usage.load_prices(ROOT / "pricing.toml")
    if cfg.model not in prices:
        raise SystemExit(f"pricing.toml has no prices for {cfg.model}")

    if args.command == "model":
        check_model(cfg)
    elif args.command == "cost":
        s = usage.summary(cfg.usage_log)
        print(f"{s['requests']} requests, ${s['cost']:.5f}")
        for lesson, spent in sorted(s["by_lesson"].items()):
            print(f"  {lesson:6} ${spent:.5f}")
    elif args.command == "prompts":
        if args.lock:
            try:
                print(f"locked {args.lock} {lock(cfg.prompts, args.lock)[:12]}")
            except PromptChanged as error:
                raise SystemExit(str(error))
        show_prompts(cfg)
    elif args.command == "show":
        show_items(cfg, args.lesson)
    else:
        try:
            load_prompt(cfg.prompts, args.prompt or cfg.prompt)   # a changed or unlocked prompt stops here, before any call
        except (PromptChanged, ValueError) as error:
            raise SystemExit(str(error))
        check_model(cfg)
        if len(args.lesson) == 1:
            results, wall = [generate_one(cfg, prices, args.lesson[0], args.prompt)], None
        else:
            results, wall = asyncio.run(generate_many(cfg, prices, args.lesson, args.prompt))
        print()
        for result in results:
            report(result)
        passed = sum(r["status"] == "passed" for r in results)
        line = f"{passed} of {len(results)} passed, ${sum(r['cost'] for r in results):.5f}"
        print(line + (f", {wall:.2f} s on the clock" if wall is not None else ""))
        return 0 if passed == len(results) else 1
    return 0
