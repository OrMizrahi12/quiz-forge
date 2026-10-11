"""Measure the graders against the reference labels: code graders first, the judge for what passes them.
Every disagreement, then agreement, Cohen's kappa and false passes. Usage: python -m evals.calibrate --split dev
(python -m quizforge eval --calibrate --split heldout also writes evals/calibration.json for the gate)"""
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


def calibrate(cfg, split, prompt=None, model=None, out=print):
    """Grade every labeled item in the split; print the disagreements and the 2x2. Returns the measured row."""
    prompt, model = prompt or SETTINGS["prompt"], model or SETTINGS["model"]
    meter = Meter(make_client(), usage.load_prices(ROOT / "pricing.toml"), model, log=cfg.usage_log, label="judge")
    table, missed = {(a, b): 0 for a in ("good", "bad") for b in ("good", "bad")}, []
    for item in [item for item in load() if item["split"] == split]:
        failed = [name for name, ok, _ in grade(item, cfg.library) if not ok]
        if failed:
            verdict, why, by = "bad", f"failed {failed[0]}", "code "
        else:
            answer = judge(meter, cfg.library, item, prompt)
            verdict, why, by = answer.verdict, answer.reason, "judge"
        table[item["label"], verdict] += 1
        miss = "" if verdict == item["label"] else (" FALSE PASS" if verdict == "good" else " false fail")
        out(f"{item['id']:12} label {item['label']:4}  {by} {verdict:4}{miss}")
        if miss:
            missed.append((item, verdict, why))
    for item, verdict, why in missed:
        out(f"\n{item['id']}: label {item['label']}: {item['reason']}\n  graders {verdict}: {why[:220]}")
    k, agree = kappa(table)
    out(f"\n{'':10} good  bad   (graders)\nlabel good {table['good', 'good']:4} {table['good', 'bad']:4}"
        f"\nlabel bad  {table['bad', 'good']:4} {table['bad', 'bad']:4}")
    out(f"agreement {agree:.0%}, kappa {k:.2f}, false passes {table['bad', 'good']}; "
        f"{meter.requests} judge requests ${meter.cost:.4f} ({model}, {prompt}, {split})")
    row = {"model": model, "prompt": prompt, "split": split, "agreement": round(agree, 3), "kappa": round(k, 3),
           "false_passes": table["bad", "good"], "false_fails": table["good", "bad"], "cost": round(meter.cost, 5)}
    (ROOT / "runs").mkdir(exist_ok=True)
    with open(ROOT / "runs/calibration.jsonl", "a") as log:  # every calibration run, kept
        log.write(json.dumps(row) + "\n")
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev")
    parser.add_argument("--prompt", default=SETTINGS["prompt"])
    parser.add_argument("--model", default=SETTINGS["model"])
    args = parser.parse_args()
    calibrate(load_config(), args.split, args.prompt, args.model)
