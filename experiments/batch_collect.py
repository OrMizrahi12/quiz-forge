"""The last batch's results, once it has ended: matched, checked and priced."""

import json

from quizforge import batch, usage
from quizforge.client import make_client
from quizforge.tools import cfg

client = make_client()
last = json.loads(batch.SENT.read_text().splitlines()[-1])
status = client.messages.batches.retrieve(last["id"])
counts = status.request_counts
if status.processing_status != "ended":
    raise SystemExit(f"{status.id}: {status.processing_status}, {counts.processing} processing. Come back later.")
took = (status.ended_at - status.created_at).total_seconds()
print(f"ended in {took:.0f} s: {counts.succeeded} succeeded, {counts.errored} errored")

prices = usage.load_prices("pricing.toml")
order, dollars = [], 0.0
for cid, outcome, used in batch.collect(client, cfg, last["id"]):
    order.append(cid)
    print(f"  {cid:9} {outcome}")
    if used:
        dollars += usage.cost(prices, cfg.model, used)
print("in the order sent:", order == last["requests"])
print(f"standard price ${dollars:.4f}, batch price ${dollars / 2:.4f}")
