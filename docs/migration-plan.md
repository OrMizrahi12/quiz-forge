# Migration plan: Quiz Forge's core and CLI to TypeScript (a planning exercise, not scheduled)

## Why, and what would justify it
- Today nothing does: the team works in Python and the tests pass. A real trigger would be a platform that only
  runs Node, or a team that maintains only TypeScript. Write the trigger down before any code moves.

## The judge first
- A parity harness: every `qf` command run against the local mock (7.1) on fixed fixtures; the Python and the
  TypeScript outputs diffed byte for byte. Proven on a build broken on purpose before it judges anything.

## The rulebook
- Types and idioms per Python construct, error handling (the 7.1 classes), the SDK's differences, naming.

## Order: the dependency map
- `python -m experiments.depmap`: level 0 has no internal imports. Port level by level, each level green on the
  harness before the next starts.

## Gaps to decide
- Pydantic validation -> a TypeScript schema library; the Agent SDK reviewer; the MCP server (keep it in Python?).

## The loop
- A shakedown on three files, thrown away. Then implement, review, fix: implementers on a smaller model,
  reviewers on a larger one, the work queue rebuilt from disk after any stop.

## Gates and stages
- Every stage: compile, unit tests, parity, the eval gate (7.4), the security checks (Module 8).
- Python stays the release until parity holds on every command; rollback is "keep shipping Python".

## Cost
- Estimated from token counts: the files' size in tokens, times the expected rounds, priced per model. A method,
  not a guess; re-estimated after the shakedown.
