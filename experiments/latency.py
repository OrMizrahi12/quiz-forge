"""Latency from here, on the platform make_client builds: 10 tiny streaming requests on generate's model; time to
the first token and to the end, p50 and p95. Point [platform] at another one to compare.
Usage: python -m experiments.latency"""
import statistics
import time
import tomllib
from datetime import UTC, datetime

from quizforge import platforms, usage
from quizforge.client import make_client
from quizforge.config import ROOT

model = tomllib.loads((ROOT / "config.toml").read_text())["route"]["generate"]["model"]
client, prices = make_client(), usage.load_prices(ROOT / "pricing.toml")
first, total = [], []
for i in range(10):
    start = time.perf_counter()
    with client.messages.stream(model=model, max_tokens=20, messages=[{"role": "user", "content": "Say ok."}]) as s:
        next(iter(s.text_stream))
        first.append(time.perf_counter() - start)
        reply, request_id = s.get_final_message(), s.request_id
    total.append(time.perf_counter() - start)
    usage.log(ROOT / "runs/usage.jsonl", time=datetime.now(UTC).isoformat(timespec="seconds"), label="latency",
              model=model, request_id=request_id, counted=None, input=reply.usage.input_tokens, cache_write=0,
              cache_read=0, output=reply.usage.output_tokens, cost=usage.cost(prices, model, reply.usage),
              seconds=round(total[-1], 2))
p95 = lambda xs: statistics.quantiles(xs, n=20)[18]
print(f"{platforms.current()} / {model}, 10 requests")
print(f"first token  p50 {statistics.median(first):.2f} s   p95 {p95(first):.2f} s")
print(f"whole reply  p50 {statistics.median(total):.2f} s   p95 {p95(total):.2f} s")
