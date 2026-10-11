"""The shared ledger, tested offline: parallel reservations never pass the limit; settling frees what wasn't spent."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from quizforge.budget import BudgetExceeded, Ledger


def test_parallel_reservations_never_pass_the_limit():
    ledger = Ledger(0.10)

    def one(n):
        try:
            return ledger.reserve(f"agent {n % 3}", 0.01)
        except BudgetExceeded:
            return 0

    with ThreadPoolExecutor(20) as pool:
        held = list(pool.map(one, range(50)))
    assert sum(1 for h in held if h) == 10 and ledger.held == pytest.approx(0.10)


def test_settling_frees_what_was_not_spent():
    ledger = Ledger(0.02)
    held = ledger.reserve("writer", 0.015)
    with pytest.raises(BudgetExceeded):
        ledger.reserve("judge", 0.01)
    ledger.settle("writer", held, 0.004)
    assert ledger.reserve("judge", 0.01) == 0.01 and ledger.by_agent == {"writer": 0.004}
