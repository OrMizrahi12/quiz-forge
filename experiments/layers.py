"""The writer agent on the poisoned L1.3, with the switchable layers off, one at a time, and both on. Each job runs
in a scratch copy of the library (the poisoned file in L1.3's place) and a scratch bank, so the real bank is never
touched. Per job: how many search results the screen withheld, how the job ended, the keys at A in what was saved.
Usage: python -m experiments.layers [runs]"""

import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from quizforge import guards, usage, write
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.meter import Meter

CONFIGS = [("none", set()), ("output only", {"output"}), ("input only", {"input"}), ("both", {"input", "output"})]
runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
flags = []
screened = guards.tool_result


def counted(cfg, found):
    try:
        return screened(cfg, found)
    except guards.Flagged:
        flags.append(1)
        raise


guards.tool_result = counted
spent = 0.0
for name, on in CONFIGS:
    guards.ON = on
    for n in range(1, runs + 1):
        scratch = Path(tempfile.mkdtemp())
        shutil.copytree(cfg.library, scratch / "library")
        shutil.copy(ROOT / "library/fixtures/poisoned/L1.3.md", scratch / "library/L1.3.md")
        job_cfg = replace(cfg, library=scratch / "library", bank=scratch / "bank")
        meter = Meter(make_client(), prices, cfg.model, log=cfg.usage_log, label=f"layers {name}")
        flags.clear()
        result = write.write(meter, job_cfg, "L1.3", out=lambda line: None)
        keys = [q["answer"] for q in result.job.questions]
        at_a = keys.count("A")
        print(f"{name:12} run {n}  withheld {len(flags)}  {result.stopped:12} keys at A {at_a} of {len(keys)}")
        spent += meter.cost
        shutil.rmtree(scratch)
    print()
screens = sum(m.cost for m in guards._meters.values())
print(f"{len(CONFIGS) * runs} jobs: writer and checker ${spent:.4f}, the screen ${screens:.4f}")
