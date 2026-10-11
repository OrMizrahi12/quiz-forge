"""One budget for several agents. Each request reserves its worst case before it is sent (counted input plus
max_tokens, priced) and settles to its real cost after; a reservation that would cross the limit is refused, so the
total can't pass the limit even with agents running in parallel."""
import threading


class BudgetExceeded(Exception):
    """The next request could take the job over its budget: it isn't sent."""


class Ledger:
    def __init__(self, limit_usd):
        self.limit, self.spent, self.held, self.by_agent = limit_usd, 0.0, 0.0, {}
        self.lock = threading.Lock()  # agents in other threads reserve and settle on the same numbers

    def reserve(self, agent, worst):
        with self.lock:
            if self.spent + self.held + worst > self.limit:
                raise BudgetExceeded(f"{agent}: ${worst:.4f} more could pass the ${self.limit} budget")
            self.held += worst
        return worst

    def settle(self, agent, held, actual):
        with self.lock:
            self.held -= held
            self.spent += actual
            self.by_agent[agent] = self.by_agent.get(agent, 0.0) + actual
