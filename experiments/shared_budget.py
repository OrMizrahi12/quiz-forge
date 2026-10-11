"""Three agents, one budget: a writer, a checker and a reviewer work through the same lessons in parallel, every
request metered on one Ledger. Each request holds its worst case before it is sent, so the total can't pass the
limit. Usage: python -m experiments.shared_budget [LIMIT_USD]"""
import sys
from concurrent.futures import ThreadPoolExecutor

from quizforge import usage
from quizforge.budget import BudgetExceeded, Ledger
from quizforge.client import make_client
from quizforge.config import ROOT, load_config
from quizforge.library import load_lesson
from quizforge.meter import Meter
from quizforge.sanitize import clean

LESSONS = ["L1.3", "L2.1", "L2.2", "L2.4", "L3.2", "L3.3"]
AGENTS = {"writer": ("claude-haiku-4-5-20251001", "Write one practice question on this lesson."),
          "checker": ("claude-haiku-5-5", "Quote the one sentence that best states this lesson's main point."),
          "reviewer": ("claude-sonnet-5-5", "Name the lesson's hardest idea for a learner, in one sentence.")}
cfg, prices = load_config(), usage.load_prices(ROOT / "pricing.toml")
ledger = Ledger(float(sys.argv[1]) if len(sys.argv) > 1 else 0.05)


def work(agent):
    model, ask = AGENTS[agent]
    meter = Meter(make_client(), prices, model, log=cfg.usage_log, ledger=ledger, agent=agent)
    for lesson in LESSONS:
        meter.label = f"{agent} {lesson} shared budget"
        text = f'<lesson id="{lesson}">\n{clean(load_lesson(cfg.library, lesson))}\n</lesson>\n\n{ask}'
        try:
            reply = meter.messages.create(model=model, max_tokens=400, messages=[{"role": "user", "content": text}])
        except BudgetExceeded as stop:
            print(f"{agent:8} {lesson}  stopped: {stop}")
            return
        print(f"{agent:8} {lesson}  ${usage.cost(prices, model, reply.usage):.4f}   ledger ${ledger.spent:.4f} spent")


with ThreadPoolExecutor(len(AGENTS)) as pool:
    list(pool.map(work, AGENTS))
spent = ", ".join(f"{agent} ${dollars:.4f}" for agent, dollars in ledger.by_agent.items())
print(f"\nspent ${ledger.spent:.4f} of ${ledger.limit}: {spent}")
