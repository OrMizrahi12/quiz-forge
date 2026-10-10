"""Every lesson in the library as one batch, and one request broken on purpose."""

from quizforge import batch
from quizforge.client import make_client
from quizforge.library import lesson_ids
from quizforge.tools import cfg

client = make_client()
reqs = list(batch.requests(cfg, lesson_ids(cfg.library)))
broken = {**reqs[0]["params"], "max_tokens": 100_000}  # over Haiku 4.5's limit
reqs.append({"custom_id": "broken", "params": broken})

sent = batch.submit(client, reqs)
print(f"{len(reqs)} requests: {reqs[0]['custom_id']}, {reqs[1]['custom_id']}, ... {reqs[-1]['custom_id']}")
print(f"{sent.id}: {sent.processing_status}, {sent.request_counts.processing} processing")
