# Runbook: Quiz Forge in operation

## Export approved items (FR-7)

- Run: `.venv/bin/python -m quizforge export --format csv` (or `md` for the review sheet). Writes to `runs/exports/`.
- Before: `.venv/bin/python -m quizforge.security.integrity` says the approved bank is intact (8.2).
- Check: one row per approved question; the row count equals `qf bank`'s approved count.
- No API call: the export reads files only and costs nothing.

## Every day

- `.venv/bin/python -m quizforge report --since 1d`: cost and latency per feature against the budgets (7.6).
- A failed CI check on main or a budget breach: open an issue, label it `ops`, link the run.

## Who decides

- Merges to main: a person, after the checks pass. Claude Code proposes; it never merges.
- A model or prompt change: only through a pull request with the eval gate (7.4).
