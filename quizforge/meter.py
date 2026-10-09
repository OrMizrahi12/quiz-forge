"""Count, time and price every Messages request a job sends, whoever sends it."""
import time

from quizforge import usage


class Meter:
    """Wraps the client: code that calls client.messages.create gets a meter instead, unchanged."""

    def __init__(self, client, prices, model):
        self.client, self.prices, self.model = client, prices, model
        self.requests, self.tokens_in, self.tokens_out, self.cost = 0, 0, 0, 0.0
        self.start = time.perf_counter()
        self.messages = self

    def create(self, **request):
        reply = self.client.messages.create(**request)
        self.requests += 1
        self.tokens_in += reply.usage.input_tokens
        self.tokens_out += reply.usage.output_tokens
        self.cost += usage.cost(self.prices, self.model, reply.usage)
        return reply

    def count_tokens(self, **request):
        return self.client.messages.count_tokens(**request)   # free, and not counted

    def seconds(self):
        return time.perf_counter() - self.start
