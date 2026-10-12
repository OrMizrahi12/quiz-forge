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

## Model upgrade (a release, never a quick edit)

1. Read the new model's migration guide. On a branch, apply its list with Claude Code: `/claude-api migrate`. The
   model id changes in `config.toml` only. Read the diff against the guide's list before anything runs.
2. The rule is written before the runs (`evals/writer.py` `decide`): no rate falls more than `[eval] allowance` below
   the baseline, and a done job stays within its budget.
3. Run the baseline, then the candidate, on the same lessons with the same judge:
   `python -m evals.writer --model <pinned>`, then `python -m evals.writer --model <candidate> --against <pinned>`.
4. Read every job that didn't finish, not only the totals. A failure can be our code, not the model.
5. Ship through a pull request: a MINOR version, a CHANGELOG entry with the evidence, a tag after the merge.
6. Watch `qf report --by model` for a week. Keep the eval suite running.
7. Roll back with one revert: `git revert -m 1 <the merge commit>`, then a PATCH release. Nothing else changes.

## Deprecation watch

- Monthly and before every release: `python -m quizforge.release --check`. It exits 1 on an alias, a model missing
  from `models.lock.toml`, or a model the Models API calls deprecated or retired.
- Re-read the deprecations page; update the lock's dates in the same commit.
- "active, watch": the earliest retirement date is under 60 days away. A deprecation notice gives at least 60 days,
  so plan the upgrade now.
