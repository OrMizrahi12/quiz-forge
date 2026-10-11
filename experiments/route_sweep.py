"""Which model and effort should generate use? The same 6 lessons on each route, graded by code and the calibrated
judge: lessons completed, items judged good, cost per completed lesson, p95 seconds. Usage: python -m
experiments.route_sweep   (about 4 minutes, about $0.20 with the judge)"""
import json
import statistics
import time

from evals.graders import grade
from evals.judge import SETTINGS, judge
from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.generate import generate_one
from quizforge.meter import Meter

LESSONS = ["L0.1", "L1.1", "L1.3", "L2.1", "L2.2", "L3.2"]  # 1,600 to 5,100 tokens of prompt
ROUTES = [{"model": "claude-haiku-4-5-20251001", "max_tokens": 1500},  # today's route; no effort parameter
          {"model": "claude-haiku-5-5", "effort": "low", "max_tokens": 1500},
          {"model": "claude-haiku-5-5", "effort": "low", "max_tokens": 4000},  # room for thinking
          {"model": "claude-sonnet-5-5", "effort": "low", "max_tokens": 1500}]
cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
meter = Meter(make_client(), prices, SETTINGS["model"], log=cfg.usage_log, label="judge route sweep")
table = []
for route in ROUTES:
    model = route["model"].removeprefix("claude-").split("-20")[0]  # without the snapshot date
    name = f"{model:10} {route.get('effort', '-'):4} {route['max_tokens']}"
    done, good, items, seconds = [], 0, 0, []
    for lesson in LESSONS:
        start = time.perf_counter()
        result = generate_one(cfg, prices, lesson, route=route, out=lambda line: None)
        seconds.append(time.perf_counter() - start)
        found = [{"lesson": lesson, "item": q} for q in result.get("questions", [])]
        passed = [item for item in found if all(ok for _, ok, _ in grade(item, cfg.library))]
        judged = sum(judge(meter, cfg.library, item).verdict == "good" for item in passed)
        good, items = good + judged, items + len(found)
        if result["status"] == "passed":
            done.append(result["cost"])
        why = "" if result["status"] == "passed" else result["problems"][0][:60]
        print(f"{name}  {lesson}  {result['status']:10} good {judged}/{len(found)}  ${result['cost']:.4f}  {why}")
    p95 = statistics.quantiles(seconds, n=20)[-1]
    table.append((name, len(done), good, items, sum(done) / max(len(done), 1), p95))
(ROOT / "runs/route_sweep.json").write_text(json.dumps(table, indent=1))  # kept with the other run records
print("\nroute                  completed  judged good  per completed lesson  p95")
for name, done, good, items, per_lesson, p95 in table:
    print(f"{name:22} {done}/{len(LESSONS):<8} {good:2}/{items:<9} ${per_lesson:.4f}{'':14}{p95:5.1f} s")
