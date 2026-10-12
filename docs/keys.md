# Keys and identity

| Environment | Workspace | Credential | Expiry |
|---|---|---|---|
| A developer's laptop | dev | a personal key, in `.env` (git ignores it) | 30 days at most |
| CI (GitHub Actions) | ci | Workload Identity Federation: no stored key | an hour at most, minted per run |
| Production | prod | a service account: federation, or a key in a secrets manager | rotated every 90 days |

- One workspace per environment: limits, caches and files stay apart, and each request's workspace is in its response
  (`python -m quizforge.whoami`).
- Personal keys act as one person and stop working when they leave; anything shared runs as a service account.
  Workspace keys are legacy.
- Rotate: create the new key, deploy it, check `whoami` and the usage pages show traffic on it, disable the old key,
  delete it after a quiet week.
- A leak: disable the key at once (reversible), rotate, run `python -m quizforge.security.secret_scan --history`, and
  read the key's usage for anything unexpected.
- Who did what: the Console's usage pages and the Usage and Cost API (an admin key) group spend by key and workspace;
  our own logs never hold a key (8.2 redacts them).
- No key reaches git: the pre-commit hook in `.githooks/` scans every commit (`git config core.hooksPath .githooks`).
