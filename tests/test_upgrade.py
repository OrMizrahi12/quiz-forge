"""9.5: the model upgrade rule, written before the runs: no rate falls more than the allowance below the
baseline, and a done lesson stays within the write job's budget."""

from evals.writer import decide

BASE = {"done": 1.0, "code": 1.0, "supported": 1.0, "good": 0.75, "usd_per_done": 0.01}


def test_the_upgrade_rule_ships_within_the_allowance_and_budget():
    assert decide(BASE, {**BASE, "good": 0.5}, 0.25, 0.15) == []


def test_the_upgrade_rule_holds_on_a_drop_or_cost():
    assert decide(BASE, {**BASE, "done": 0.5}, 0.25, 0.15)
    assert decide(BASE, {**BASE, "usd_per_done": 0.2}, 0.25, 0.15)
