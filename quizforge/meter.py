"""Count, time and price every Messages request a job sends, whoever sends it."""

import time
from datetime import datetime, timezone

from quizforge import usage


class Meter:
    """Wraps the client: code that calls client.messages.create gets a meter instead, unchanged.
    log: a usage log path; then every request is also logged there, under the meter's current label."""

    def __init__(self, client, prices, model, log=None, label=""):
        self.client, self.prices, self.model, self.log, self.label = client, prices, model, log, label
        self.requests, self.tokens_in, self.tokens_out, self.cost = 0, 0, 0, 0.0
        self.counted = None  # the last count_tokens result, logged with the request that follows it
        self.start = time.perf_counter()
        self.messages = self

    def create(self, **request):
        sent = time.perf_counter()
        reply = self.client.messages.create(**request)
        spent = usage.cost(self.prices, self.model, reply.usage)
        self.requests += 1
        self.tokens_in += reply.usage.input_tokens
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

    def count_tokens(self, **request):
        counted = self.client.messages.count_tokens(**request)  # free, and not counted as a request
        self.counted = counted.input_tokens
        return counted

    def seconds(self):
        return time.perf_counter() - self.start
