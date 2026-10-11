"""Measure the graders against the reference labels: code graders first, the judge for what passes them.
Every disagreement, then agreement, Cohen's kappa and false passes. Usage: python -m evals.calibrate --split dev"""
import argparse
import json

from evals.graders import grade, load
from evals.judge import SETTINGS, judge
from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter


def kappa(table):
    """Agreement beyond chance: 1 is perfect, 0 is what guessing at the same rates would get."""
    n = sum(table.values())
    seen = (table["good", "good"] + table["bad", "bad"]) / n
    chance = sum((table[k, "good"] + table[k, "bad"]) * (table["good", k] + table["bad", k]) for k in ("good", "bad"))
    return (seen - chance / n**2) / (1 - chance / n**2), seen


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev")
    parser.add_argument("--prompt", default=SETTINGS["prompt"])
    parser.add_argument("--model", default=SETTINGS["model"])
    args = parser.parse_args()
    cfg = load_config()
    meter = Meter(make_client(), usage.load_prices(ROOT / "pricing.toml"), args.model, log=cfg.usage_log,
                  label="judge")
    table, missed = {(a, b): 0 for a in ("good", "bad") for b in ("good", "bad")}, []
    for item in [item for item in load() if item["split"] == args.split]:
        failed = [name for name, ok, _ in grade(item, cfg.library) if not ok]
        if failed:
            verdict, why, by = "bad", f"failed {failed[0]}", "code "
        else:
            answer = judge(meter, cfg.library, item, args.prompt)
            verdict, why, by = answer.verdict, answer.reason, "judge"
        table[item["label"], verdict] += 1
        miss = "" if verdict == item["label"] else (" FALSE PASS" if verdict == "good" else " false fail")
        print(f"{item['id']:12} label {item['label']:4}  {by} {verdict:4}{miss}")
        if miss:
            missed.append((item, verdict, why))
    for item, verdict, why in missed:
        print(f"\n{item['id']}: label {item['label']}: {item['reason']}\n  graders {verdict}: {why[:220]}")
    k, agree = kappa(table)
    print(f"\n{'':10} good  bad   (graders)\nlabel good {table['good', 'good']:4} {table['good', 'bad']:4}"
          f"\nlabel bad  {table['bad', 'good']:4} {table['bad', 'bad']:4}")
    print(f"agreement {agree:.0%}, kappa {k:.2f}, false passes {table['bad', 'good']}; "
          f"{meter.requests} judge requests ${meter.cost:.4f} ({args.model}, {args.prompt}, {args.split})")
    row = {"model": args.model, "prompt": args.prompt, "split": args.split, "agreement": round(agree, 3),
           "kappa": round(k, 3), "false_passes": table["bad", "good"], "cost": round(meter.cost, 5)}
    with open(ROOT / "runs/calibration.jsonl", "a") as log:  # every calibration run, kept
        log.write(json.dumps(row) + "\n")
