# How a change ships

| Where | What runs | What it costs | Blocks a merge? |
|---|---|---|---|
| Your laptop, on every save | `python -m pytest -q`: unit, contract and functional tests, offline (a guard fails any test that connects) | nothing | no, but CI runs the same |
| Your laptop, on purpose | `pytest -m integration` (the real API) and `pytest -m e2e` (the local mock) | under a cent | no |
| Pull request touching `prompts/`, `quizforge/`, `evals/`, `config.toml` or `pricing.toml` | the `unit` job, then the `gate` job: `python -m quizforge eval --gate --max-usd 0.10` | at most $0.10 a run; superseded runs are cancelled | yes: a FAIL row fails the job |
| `main`, after a merge | nothing automatic | | |

What the gate checks, in order:

1. **The judge first.** `evals/calibration.json` must come from the held-out labels and match the judge in `config.toml` (model, rubric version, the rubric's locked hash). Otherwise the gate stops before any request.
2. **The criteria.** Completion, quotes, cost and latency against `[eval]` in `config.toml` (it mirrors `evals/criteria.md`). Quality is gated only while the judge meets its own line on held-out; until then it is reported, not gated.
3. **The baseline.** Each rate against `evals/baseline.json`; a fall bigger than `allowance` fails.

What only a person decides:

- Merging a pull request.
- `python -m quizforge eval --accept`, on `main`: the last passing gate run becomes the new baseline. CI never moves its own baseline.
- A new judge: calibrate it once on held-out (`python -m quizforge eval --calibrate --split heldout`), commit `evals/calibration.json`, and the gate trusts it from then on.
