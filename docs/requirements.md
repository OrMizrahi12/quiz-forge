# Quiz Forge v1.0: requirements (from docs/request.md)

Each requirement has a number, the phrase it comes from, and the check that proves it.

## Functional: what it must do

| # | Requirement | Source phrase | Acceptance test |
|---|---|---|---|
| FR-1 | Load any course library from a folder | "any of our courses" | a second library generates and passes |
| FR-2 | Read an exam blueprint with domain weights | "its own exam blueprint" | items per domain match the weights |
| FR-3 | Generate items for a domain, two per lesson | "practice exams" | `qf generate` writes schema-valid items |
| FR-4 | Every item quotes its lesson word for word | "point to the lesson text" | eval `quotes` = 100% |
| FR-5 | No item reaches learners without a reviewer's yes | "a reviewer ... approves" | only `qf review` approves |
| FR-6 | Regenerate one item on request | "asks to regenerate" | `qf generate --lesson <id>` |
| FR-7 | Export approved items to the platform format | "import format" | the export passes their schema |

## Infrastructure and quality: how well, under what limits

| # | Requirement | Number | Check |
|---|---|---|---|
| NFR-1 | Volume | 2,000 approved items a quarter | `experiments/capacity.py` |
| NFR-2 | Latency, regenerate | p95 under 60 s | the eval gate's p95 |
| NFR-3 | Latency, bulk | overnight, done by 07:00 | the nightly job's log |
| NFR-4 | Cost | generate within the quarter budget | `qf report` per feature |
| NFR-5 | Data residency | US-only: `inference_geo="us"` | Haiku 4.5: a 400; Haiku 5.5, our route: 1.1x |
| NFR-6 | No learner data in any request | 0 learner fields | the data map (8.2) and redaction tests |
| NFR-7 | Quality | eval criteria (7.3) on every change | the CI gate |
| NFR-8 | Maintainability | pinned models; 60 days' notice handled | a deprecation check |

## Open questions back to Northwind

- "Fast": the 60 s regenerate is the only latency they named. Is overnight fine for bulk?
- "Secure": beyond no learner data and US-only, who may approve, and how long are logs kept?
- "A lot of content": how many courses, and how many lessons in the largest one?
- The quarter budget: a number, and who gets the alert at 80%?
