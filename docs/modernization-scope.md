# Modernization scope (a hypothetical client: an invented regional insurer's legacy claims service)

| | |
|---|---|
| Goal | Move the claims service off an unsupported runtime with no change in behavior |
| Not in scope | New features, a new data model, a UI redesign |
| Discovery | Inventory, a dependency graph, dead code, the test coverage baseline |
| The judge | A parity harness and data fixtures agreed with the client, before any port |
| Stages | Each with exit criteria: parity on its modules, tests, a security review |
| Who approves | The client's tech lead signs off each stage; nothing merges without a person's review |
| Claude's role | Writes and reviews code in a sandbox; no production data; no merges |
| Estimate | Token counts per module times rounds, priced per model, revised after the shakedown |
| Risks | Hidden behavior the fixtures miss; vendor libraries with no equivalent; data migration |
| Security | See `docs/security-review.md` (6.5) |
