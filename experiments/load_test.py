"""A load test against the local mock, never the real API: the same 80 small requests at each concurrency level,
the mock limited to 240 requests per minute (scaled down so the effect shows in seconds). Usage:
python -m experiments.load_test 2 8 32"""
import asyncio
import statistics
import sys
import time

import anthropic

from experiments.mock_api import serve

REQUESTS, RPM = 80, 240


async def one(client, slots, seconds):
    async with slots:
        start = time.perf_counter()
        try:
            await client.messages.create(model="claude-haiku-4-5", max_tokens=20,
                                         messages=[{"role": "user", "content": "Hi"}])
        except anthropic.RateLimitError:  # 429 again after every retry
            return False
        seconds.append(time.perf_counter() - start)
        return True


async def level(n):
    mock = serve(["200"], rpm=RPM, latency=(0.5, 0.2), quiet=True)
    client = anthropic.AsyncAnthropic(base_url="http://127.0.0.1:8787", api_key="mock-not-a-real-key", max_retries=4)
    slots, seconds, start = asyncio.Semaphore(n), [], time.perf_counter()
    done = await asyncio.gather(*(one(client, slots, seconds) for _ in range(REQUESTS)))
    wall = time.perf_counter() - start
    mock.shutdown()
    mock.server_close()
    p50, p95 = statistics.median(seconds), statistics.quantiles(seconds, n=20)[-1]
    print(f"N={n:<3} done {sum(done):3}/{REQUESTS}  429s {mock.statuses.count(429):4}  {wall:5.1f} s  "
          f"{sum(done) / wall:4.1f} req/s  p50 {p50:4.1f} s  p95 {p95:4.1f} s")


for n in map(int, sys.argv[1:] or ["2", "8", "32"]):
    asyncio.run(level(n))
