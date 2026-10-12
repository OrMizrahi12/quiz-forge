"""Can a request run in the US only? One tiny request with inference_geo="us" per model: the one that answers
records its usage and the account's rate limits from the response headers (runs/limits.json, for capacity.py).
Usage: python -m experiments.residency"""
import json
import time
from datetime import UTC, datetime

import anthropic

from quizforge import usage
from quizforge.client import make_client
from quizforge.config import ROOT

MODELS = ["claude-haiku-4-5-20251001", "claude-haiku-5-5"]
LIMITS = ("requests", "input-tokens", "output-tokens")
client, prices = make_client(), usage.load_prices(ROOT / "pricing.toml")

for model in MODELS:
    request = dict(model=model, max_tokens=20, inference_geo="us",
                   messages=[{"role": "user", "content": "Reply with the word ok."}])
    sent = time.perf_counter()
    try:
        raw = client.messages.with_raw_response.create(**request)
    except anthropic.BadRequestError as e:
        print(f"{model:26} {e.status_code}  {e.body['error']['message']}")
        continue
    reply = raw.parse()
    spent = usage.cost(prices, model, reply.usage) * 1.1  # US-only inference: 1.1x on 4.6 and later models
    usage.log(ROOT / "runs/usage.jsonl", time=datetime.now(UTC).isoformat(timespec="seconds"),
              label="residency", model=model, request_id=raw.request_id, counted=None,
              input=reply.usage.input_tokens, cache_write=0, cache_read=0, output=reply.usage.output_tokens,
              cost=spent, seconds=round(time.perf_counter() - sent, 2))
    print(f"{model:26} 200  inference_geo={reply.usage.inference_geo}  ${spent:.6f}  {raw.request_id}")
    limits = {name: int(raw.headers[f"anthropic-ratelimit-{name}-limit"]) for name in LIMITS}
    (ROOT / "runs/limits.json").write_text(json.dumps({"model": model, "date": f"{datetime.now(UTC):%Y-%m-%d}",
                                                       **limits}, indent=1) + "\n")
    print(f"{'':26} limits per minute: {limits}")
