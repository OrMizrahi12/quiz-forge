"""Count, time and price every Messages request a job sends, whoever sends it."""

import time
from datetime import datetime, timezone

from quizforge import usage


class Meter:
    """Wraps the client: code that calls client.messages.create gets a meter instead, unchanged.
    log: a usage log path; then every request is also logged there, under the meter's current label."""

    def __init__(self, client, prices, model, log=None, label="", ledger=None, agent=""):
        self.client, self.prices, self.model, self.log, self.label = client, prices, model, log, label
        self.ledger, self.agent = ledger, agent  # a shared budget (quizforge/budget.py), and who spends
        self.requests, self.tokens_in, self.tokens_out, self.cost = 0, 0, 0, 0.0
        self.counted = None  # the last count_tokens result, logged with the request that follows it
        self.start = time.perf_counter()
        self.messages = self

    def create(self, **request):
        sent = time.perf_counter()
        held = self.reserve(request) if self.ledger else 0.0
        try:
            reply = self.client.messages.create(**request)
        except Exception:
            if self.ledger:
                self.ledger.settle(self.agent, held, 0.0)  # nothing was spent: free the reservation
            raise
        spent = usage.cost(self.prices, self.model, reply.usage)
        if self.ledger:
            self.ledger.settle(self.agent, held, spent)
        self.requests += 1
        u = reply.usage  # all the input, cached or not (the GenAI convention, 7.2)
        cached = (getattr(u, "cache_creation_input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
        self.tokens_in += u.input_tokens + cached
        self.tokens_out += reply.usage.output_tokens
        self.cost += spent
        if self.log:
            usage.log(
                self.log,
                time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                label=self.label,
                model=self.model,
                request_id=getattr(reply, "_request_id", None),
                counted=self.counted,
                input=reply.usage.input_tokens,
                cache_write=getattr(reply.usage, "cache_creation_input_tokens", 0) or 0,
                cache_read=getattr(reply.usage, "cache_read_input_tokens", 0) or 0,
                output=reply.usage.output_tokens,
                cost=spent,
                seconds=round(time.perf_counter() - sent, 2),
            )
        return reply

    def reserve(self, request):
        """Hold this request's worst case on the ledger before it is sent: refused if it doesn't fit."""
        sized = {key: request[key] for key in ("model", "system", "messages", "tools") if key in request}
        counted = self.client.messages.count_tokens(**sized).input_tokens
        worst = usage.worst_case(self.prices, self.model, counted, request["max_tokens"])
        return self.ledger.reserve(self.agent, worst)

    def count_tokens(self, **request):
        counted = self.client.messages.count_tokens(**request)  # free, and not counted as a request
        self.counted = counted.input_tokens
        return counted

    def seconds(self):
        return time.perf_counter() - self.start
