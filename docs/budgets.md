# Budgets per feature (from the usage log, Module 7)

Each feature gets three numbers: what one task may cost, how long a request may take (p95), and how often the task
must finish. `python -m quizforge.report` holds the log against the first two (config.toml `[budget.*]`) and exits 1
on a breach, so a scheduler or CI can alert.

| Feature | One task | Cost per task | p95 per request | Must finish |
|---|---|---|---|---|
| generate | a lesson, repairs included | $0.02 | 30 s | 95% within 2 repairs |
| judge | one verdict | $0.01 | 20 s | every item past the code graders |
| eval gate (CI) | a run on 4 lessons | $0.10 (`--max-usd`) | 15 min a job | every pull request it gates |
| write | one agent job | $0.15 (`[write] max_usd`) | 60 s | done, or stopped with a reason |
| ask | one question | $0.05 (`[ask] max_usd`) | 20 s | an answer or "not found" |

Per-request caps stay as they are: `max_request_usd` refuses a request whose worst case is over $0.02.

Backstops outside the code: the workspace's monthly spend limit, set by the account owner in the Console. A request
over it fails, and retry.py classifies that as stop, never as wait.
