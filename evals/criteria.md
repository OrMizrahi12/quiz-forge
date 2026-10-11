# What "done" means for generate (written before the first eval run)

Measured on the 10 lessons in evals/cases.jsonl, Claude Haiku 4.5, the prompt version in config.toml:

- Completion: at least 9 of 10 lessons pass the code graders within 2 repairs.
- Quotes: 0 items with a quote that isn't word for word in its lesson (a hard rule: 100%).
- Quality: at least 80% of the items are judged good by the calibrated judge.
- Cost: at most $0.02 per completed lesson, repairs included.
- Latency: p95 at most 30 s per lesson.

The judge itself, on the held-out reference labels it has never seen:

- Agreement at least 90%, Cohen's kappa at least 0.7.
- At most 1 false pass (a bad item judged good): a false pass reaches learners.
