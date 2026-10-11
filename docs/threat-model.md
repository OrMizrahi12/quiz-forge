# Threat model

What we protect: the approved bank (learners trust its answers), the API key, the logs, and any personal data a
lesson carries.

| Way in | Who controls it | What an attacker wants | Layers that answer it |
|---|---|---|---|
| A lesson file | whoever wrote it | change the questions (8.1: every key at A) | input screen, keys placed by code, the checker, a person's review |
| A search or tool result | the same files, read by an agent | steer the agent | input screen; three tools only (`security/policy.toml`) |
| Personal data in a lesson | a reader | reach the API, the logs, another user | minimize, redact, one memory folder per user (8.2) |
| A pull request | a contributor | weaken a check or a prompt | offline tests and the eval gate in CI; a person merges |
| The machine and its `.env` | us | the key | 8.5 |

No single layer is trusted alone: `experiments/layers.py` turns the switchable ones off one at a time.
Out of scope: Anthropic's side of the API (see its data-retention docs), and a person who approves a bad item on
purpose.
