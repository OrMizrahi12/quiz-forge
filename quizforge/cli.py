import argparse
import asyncio

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_many, generate_one


def check_model(cfg):
    """The pinned model, checked against the Models API: it must exist and not be retired."""
    info = make_client().models.retrieve(cfg.model)
    print(f"{info.id} | {info.lifecycle} | retires {info.retires_at or 'not scheduled'}")
    if info.lifecycle == "retired":
        raise SystemExit(f"{cfg.model} is retired: pick its replacement, follow the migration guide, rerun your evals")
    if info.lifecycle == "deprecated":
        print(f"warning: {cfg.model} is deprecated; plan the move before {info.retires_at}")
    return info


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m quizforge", description="Quiz Forge v0: practice questions from lesson notes")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="write practice questions for one or more lessons")
    gen.add_argument("--lesson", action="append", required=True, help="a lesson id, e.g. L1.3 (repeat for several)")
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
    elif len(args.lesson) == 1:
        check_model(cfg)
        _, _, rows = generate_one(cfg, prices, args.lesson[0])
        for row in rows:
            print(f"\n\n{row['counted']} counted, {row['input']} in, {row['output']} out, ${row['cost']:.5f}, "
                  f"{row['seconds']} s, request {row['request_id']}")
    else:
        check_model(cfg)
        rows, wall = asyncio.run(generate_many(cfg, prices, args.lesson))
        print(f"\n{len(rows)} lessons, ${sum(r['cost'] for r in rows):.5f}, {sum(r['seconds'] for r in rows):.2f} s of waiting, "
              f"{wall:.2f} s on the clock")
    return 0
