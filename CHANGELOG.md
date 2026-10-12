# Changelog

Quiz Forge uses semantic versions, MAJOR.MINOR.PATCH:
- MAJOR: a change that breaks what others rely on: the item schema, the CLI's commands or flags, the export format.
- MINOR: a new feature that breaks nothing. A model change or a new prompt version is at least MINOR, and always
  listed here with its evidence.
- PATCH: a fix that changes no behavior anyone relies on.

Each release is a git tag, `v<version>`. `python -m quizforge.release` prints exactly what a release is made of.

## 0.10.0 (2026-10-12)
The writer moves to `claude-haiku-5-5` (9.5). The evidence: `evals/writer.py`, the same 4 regression lessons
on each model, graded by code and by the same judge; the rule was written before the runs.
- `claude-haiku-4-5-20251001`: done 100%, code 88%, checker 100%, judge good 62%, $0.0509 per done lesson.
- `claude-haiku-5-5`: done 100%, code 75%, checker 100%, judge good 62%, $0.0047 per done lesson.
- Fixed in our code first: the checker's verdict is read from the word after the colon (the new model adds a reason); the writer has its own max_tokens, with room for thinking; every tool error carries a message (an empty one made the API refuse the request).
- Rollback: `git revert -m 1` on this release's merge commit, then a PATCH release.

## 0.9.0 (2026-10-12)
The first release with a version and a tag. Everything since Lab 1 shipped as 0.1.0; this entry sums it up.
- From a business need to v1.0 on paper: requirements with acceptance tests, a capacity model from our own logs,
  US-only inference checked per model (9.1).
- `qf export --format csv`, built on a branch and merged through a reviewed pull request; a runbook (9.2).
- One client factory, contract tests first; a staged migration plan (9.3).
- A platform setting in the client factory, a capability check, ADR 0001 (9.4).
- Security: an injection screen, data minimization and redaction, layered guardrails, one destructive-action policy
  for Claude Code and the SDK, a secret scan in git and CI (Module 8).
- Models: generate on `claude-haiku-5-5` at low effort (measured, 7.6); the writer on `claude-haiku-4-5-20251001`;
  the judge and the SDK reviewer on `claude-sonnet-5-5`.
- Prompts: `item_writer` v4, `judge` v2, both locked.

## Earlier milestones, untagged
- v0.7 (Module 7): errors with a recovery decision each, tracing, evals with a calibrated judge, a CI gate, caching, budgets.
- v0.6 (Module 6): the course-library MCP server and `qf ask`.
- v0.5 (Module 5): Claude Code tools as plugins, an Agent SDK reviewer.
