import argparse
import asyncio
import json
import re
import sys
import tomllib
from dataclasses import replace
from datetime import date

import anyio

from quizforge import ask, batch, export, review, sources, tracing, usage, write
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.evidence import evidence
from quizforge.generate import generate_many, generate_one
from quizforge.library import lesson_ids
from quizforge.library_client import connect
from quizforge.meter import Meter
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
    for line in path.read_text().splitlines() if path.exists() else []:
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
        print(f'   Answer: {q["answer"]}. {q["why"]}\n   Quote: "{q["quote"]}"')
    for problem in result.get("problems", []):
        print(f"  problem: {problem}")


def saved(cfg, lesson_id):
    path = cfg.output_dir / f"{lesson_id}.json"
    if not path.exists():
        raise SystemExit(f"no passed questions for {lesson_id}: run generate --lesson {lesson_id}")
    return json.loads(path.read_text())


def check_items(cfg, prices, lesson_id):
    """Claude checks each saved question's quote with our check_quote tool, then judges it."""
    result = saved(cfg, lesson_id)
    verdicts, calls, usages = sources.review(make_client(), cfg, lesson_id, result["questions"])
    spent = sum(usage.cost(prices, cfg.model, u) for u in usages)
    for line in verdicts:
        print(line)
    print(f"{calls} check_quote call(s), {len(usages)} request(s), ${spent:.5f}")
    result["review"] = verdicts
    (cfg.output_dir / f"{lesson_id}.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if verdicts and all(sources.supported(line) for line in verdicts) else 1


def show_evidence(cfg, prices, lesson_id):
    """The lesson's PDF (uploaded once) and the passages, with pages, that support each answer."""
    claims, used, uploaded = evidence(make_client(), cfg, lesson_id, saved(cfg, lesson_id)["questions"])
    print(
        f"{lesson_id}.pdf: {'uploaded' if uploaded else 'reused by file_id'}, {used.input_tokens} input tokens, "
        f"${usage.cost(prices, cfg.model, used):.5f}"
    )
    for claim in claims:
        if claim["citations"]:
            print(f"  {claim['text'][:90]}")
        for text, page in claim["citations"]:
            print(f"    [page {page}] {text[:80]!r}")


def batch_submit(cfg, lessons):
    reqs = list(batch.requests(cfg, lessons or lesson_ids(cfg.library)))
    sent = batch.submit(make_client(), reqs)
    print(
        f"{sent.id}: {len(reqs)} requests ({reqs[0]['custom_id']} ... {reqs[-1]['custom_id']}), {sent.processing_status}"
    )


def batch_collect(cfg, prices, batch_id=None):
    """Matched by custom_id, checked in code; failures repaired in realtime. 'Come back later' if it hasn't ended."""
    client = make_client()
    batch_id = batch_id or batch.last_sent()["id"]
    status = client.messages.batches.retrieve(batch_id)
    counts = status.request_counts
    if status.processing_status != "ended":
        print(f"{batch_id}: {status.processing_status}, {counts.processing} processing. Come back later.")
        return 2
    took = (status.ended_at - status.created_at).total_seconds()
    print(
        f"{batch_id} ended in {took:.0f} s: {counts.succeeded} succeeded, {counts.errored} errored, "
        f"{counts.expired} expired, {counts.canceled} canceled"
    )
    results = [batch.finish(cfg, prices, client, *row) for row in batch.collect(client, cfg, batch_id)]
    print()
    for result in sorted(results, key=lambda r: r["lesson"]):
        print(
            f"{result['lesson']:5} {result['status']:8} {result['via']:>5}, {result['attempts']} attempt(s), ${result['cost']:.5f}"
        )
    passed = sum(r["status"] == "passed" for r in results)
    print(f"{passed} of {len(results)} passed, ${sum(r['cost'] for r in results):.5f}")
    return 0 if passed == len(results) else 1


def write_lesson(cfg, prices, lesson_id):
    """The draft -> check -> revise job for one lesson. Its questions wait in bank/pending/ for review."""
    meter = Meter(make_client(), prices, cfg.model, log=cfg.usage_log)
    try:
        result = write.write(meter, cfg, lesson_id)
    except write.Waiting as error:
        raise SystemExit(str(error))
    job = result.job
    print(f"\nstopped: {result.stopped} ({result.who}, round {result.rounds} of {cfg.rounds})")
    if job.questions:
        backed = sum(sources.supported(line) for line in job.verdicts)
        print(
            f"{len(job.questions)} question(s) in bank/pending/{job.path.name}, {backed} supported by the checker: "
            f"waiting for review (python -m quizforge review --lesson {lesson_id})"
        )
    print(f"{meter.requests} request(s), {meter.tokens_in:,} input tokens, ${meter.cost:.5f}")
    return 0 if result.stopped == "done" else 1


def ask_person(prompt):
    """input(), with the answer echoed when it comes from a pipe, so the transcript shows it."""
    answer = input(prompt)
    if not sys.stdin.isatty():
        print(answer)
    return answer


def review_pending(cfg, lessons):
    if not review.pending(cfg, lessons):
        print("nothing waiting in bank/pending/")
        return 0
    decided = review.review(cfg, lessons, ask=ask_person)
    print("\n" + ", ".join(f"{lesson} {state}" for lesson, state in decided.items()))
    return 0


def show_bank(cfg):
    found = review.counts(cfg)
    if not found:
        print("bank is empty")
        return
    show_declined = any("declined" in n for n in found.values())  # the column appears once something is declined

    def line(label, n):
        text = f"{label:6} pending {n['pending']:3}   approved {n['approved']:3}"
        return text + f"   declined {n.get('declined', 0):3}" if show_declined else text

    for lesson, n in found.items():
        print(line(lesson, n))
    print(
        line("total", {key: sum(n.get(key, 0) for n in found.values()) for key in ("pending", "approved", "declined")})
    )


def ask_library(cfg, prices, question):
    """Quiz Forge as an MCP client: Claude answers through the library server's tools, within a turn limit and a budget."""
    meter = Meter(make_client(), prices, cfg.model, log=cfg.usage_log, label="ask")

    async def answer():
        async with connect() as library:
            return await ask.ask(meter, cfg, question, library)

    result = anyio.run(answer)
    if result.text:
        print(f"\n{result.text}\n")
    print(f"stopped: {result.stopped} after {result.turns} turn(s)")
    print(f"{meter.requests} request(s), {meter.tokens_in:,} input tokens, ${meter.cost:.5f}")
    return 0 if result.stopped == "done" else 1


def run_eval(cfg, prices, args):
    """qf eval: --calibrate measures the judge against people's labels and records it; --gate refuses a judge that
    isn't calibrated in its current form, then holds the regression set to the criteria and the accepted baseline."""
    from evals import gate
    from evals.calibrate import calibrate
    from evals.graders import load
    from evals.run import evaluate

    limits, judge = gate.settings()
    if args.accept:
        gate.accept()
        return 0
    if args.calibrate:
        row = calibrate(cfg, args.split)
        if args.split != "heldout":
            print("dev is for tuning: only a heldout calibration is recorded for the gate")
            return 0
        found = gate.record(
            judge, args.split, row["agreement"], row["kappa"], row["false_passes"], row["false_fails"], row["cost"]
        )
        gate.CALIBRATION.write_text(json.dumps(found, indent=1) + "\n")
        ok = gate.trusted(found, limits)
        print(
            f"wrote evals/calibration.json: the judge {'meets' if ok else 'misses'} its line (agreement "
            f"{limits['judge_agreement']:.0%}, kappa {limits['judge_kappa']}, false passes {limits['judge_false_passes']})"
        )
        return 0 if ok else 1
    calibration = gate.load(gate.CALIBRATION)
    reason = gate.stale(calibration, judge)
    if reason:
        print(f"gate: refused before any request: {reason}")
        return 1
    trusted = gate.trusted(calibration, limits)
    if not trusted:
        print("the judge missed its line on heldout: quality is reported, not gated\n")
    totals = evaluate(cfg, prices, load("regression.jsonl"), args.max_usd or limits["max_usd"])
    rows = gate.checks(totals, limits, trusted) + gate.drops(
        totals, gate.load(gate.BASELINE), limits["allowance"], trusted
    )
    gate.publish(rows)
    passed = not gate.failed(rows)
    gate.LAST_RUN.parent.mkdir(exist_ok=True)
    gate.LAST_RUN.write_text(
        json.dumps({"date": date.today().isoformat(), "passed": passed, "totals": totals}, indent=1)
    )
    print(f"gate: {'pass' if passed else 'fail'}, ${totals['spent']:.4f} spent")
    return 0 if passed else 1


def report(result):
    print(
        f"{result['lesson']}: {result['status']} after {result['attempts']} attempt(s), ${result['cost']:.5f} -> {result['path']}"
        + (f" (next: {result['decision']})" if "decision" in result else "")
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m quizforge", description="Quiz Forge: checked practice questions from lesson notes"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write checked practice questions for one or more lessons")
    gen.add_argument("--lesson", action="append", required=True, help="a lesson id, e.g. L1.3 (repeat for several)")
    gen.add_argument("--prompt", help="a locked prompt version (default: the one in config.toml)")
    show = sub.add_parser("show", help="print a lesson's saved questions")
    show.add_argument("--lesson", required=True)
    prompts = sub.add_parser("prompts", help="list the prompt versions; --lock freezes one after you measure it")
    prompts.add_argument("--lock", metavar="VERSION")
    prompts.add_argument("--folder", help="another prompt folder, e.g. prompts/judge")
    chk = sub.add_parser("check", help="Claude checks a lesson's saved questions with the check_quote tool")
    chk.add_argument("--lesson", required=True)
    evi = sub.add_parser("evidence", help="the passages, with pages, that support each saved answer (PDF, citations)")
    evi.add_argument("--lesson", required=True)
    bat = sub.add_parser("batch", help="generate as a Message Batch: half the price, results within 24 hours")
    bsub = bat.add_subparsers(dest="action", required=True)
    bsend = bsub.add_parser("submit", help="one request per lesson (default: every lesson in the library)")
    bsend.add_argument("--lesson", action="append", help="a lesson id (repeat for several)")
    bget = bsub.add_parser("collect", help="match, check and save the results; repair failures in realtime")
    bget.add_argument("--batch", help="a batch id (default: the last one submitted)")
    wri = sub.add_parser(
        "write", help="the writer agent drafts, a checker subagent checks, the writer revises; into bank/pending/"
    )
    wri.add_argument("--lesson", required=True)
    rev = sub.add_parser("review", help="a person approves or declines pending questions, one lesson at a time")
    rev.add_argument("--lesson", action="append", help="a lesson id (default: every lesson waiting)")
    sub.add_parser("bank", help="how many questions are pending and approved, per lesson")
    exp = sub.add_parser("export", help="the approved questions as a CSV or a Markdown review sheet, in runs/exports/")
    exp.add_argument("--format", choices=["csv", "md"], required=True)
    asks = sub.add_parser("ask", help="ask about the library: Claude answers with the library server's tools (MCP)")
    asks.add_argument("question")
    sub.add_parser("model", help="check the pinned model against the Models API")
    sub.add_parser("cost", help="total spend from the usage log")
    evl = sub.add_parser(
        "eval", help="--calibrate proves the judge; --gate holds generate to the criteria and baseline"
    )
    mode = evl.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--calibrate", action="store_true", help="the judge against the human labels, recorded for the gate"
    )
    mode.add_argument("--gate", action="store_true", help="the regression set against the criteria and the baseline")
    mode.add_argument(
        "--accept", action="store_true", help="a person, on main: the last passing gate run becomes the baseline"
    )
    evl.add_argument("--split", default="heldout", help="the labels to calibrate on (only heldout is recorded)")
    evl.add_argument("--max-usd", type=float, help="the gate's spend cap (default: config.toml [eval] max_usd)")
    rep = sub.add_parser("report", help="cost, latency and cache reads per feature, held against the budgets")
    rep.add_argument("--since", default="1d", help="how far back: 1d, 12h, 90m")
    rep.add_argument("--by", choices=["feature", "model"], default="feature")
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
        if args.folder:
            cfg = replace(cfg, prompts=ROOT / args.folder, prompt="")
        if args.lock:
            try:
                print(f"locked {args.lock} {lock(cfg.prompts, args.lock)[:12]}")
            except PromptChanged as error:
                raise SystemExit(str(error))
        show_prompts(cfg)
    elif args.command == "show":
        show_items(cfg, args.lesson)
    elif args.command == "eval":
        return run_eval(cfg, prices, args)
    elif args.command == "report":
        from quizforge import report as budgets

        return budgets.run(args.since, args.by)
    elif args.command == "write":
        try:
            load_prompt(cfg.prompts, cfg.prompt)  # a changed or unlocked prompt stops here, before any call
        except (PromptChanged, ValueError) as error:
            raise SystemExit(str(error))
        return write_lesson(cfg, prices, args.lesson)
    elif args.command == "review":
        return review_pending(cfg, args.lesson)
    elif args.command == "bank":
        show_bank(cfg)
    elif args.command == "export":
        return export.run(cfg, args.format)
    elif args.command == "ask":
        return ask_library(cfg, prices, args.question)
    elif args.command == "check":
        return check_items(cfg, prices, args.lesson)
    elif args.command == "evidence":
        show_evidence(cfg, prices, args.lesson)
    elif args.command == "batch":
        try:
            load_prompt(cfg.prompts, cfg.prompt)
        except (PromptChanged, ValueError) as error:
            raise SystemExit(str(error))
        cfg = replace(cfg, model=tomllib.loads((ROOT / "config.toml").read_text())["route"]["batch"]["model"])
        if args.action == "submit":
            batch_submit(cfg, args.lesson)
        else:
            return batch_collect(cfg, prices, args.batch)
    else:
        try:
            load_prompt(
                cfg.prompts, args.prompt or cfg.prompt
            )  # a changed or unlocked prompt stops here, before any call
        except (PromptChanged, ValueError) as error:
            raise SystemExit(str(error))
        print(f"trace: {tracing.setup().relative_to(ROOT)}")
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
