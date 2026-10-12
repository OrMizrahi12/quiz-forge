# ADR 0001: Where Quiz Forge runs

Status: accepted, 2026-10 (Northwind Learning's v1.0)

## Context
- From docs/requirements.md: US-only inference (NFR-5), bulk generation overnight on Batch (NFR-1, NFR-3), a
  quarterly budget (NFR-4). Quiz Forge uses structured outputs, Files, Message Batches and the Models API.
- `python -m quizforge.platforms` checks those uses against each platform's documented gaps.

## Options
| Platform | Breaks for us | Residency | Billed by |
|---|---|---|---|
| Claude API | nothing | `inference_geo` per request | Anthropic |
| Claude Platform on AWS | nothing | `inference_geo` per request | AWS |
| Amazon Bedrock | structured outputs (generate), Files, Batches, Models API | the endpoint's region | AWS |
| Google Cloud | Files, Batches, Models API | the endpoint's region | Google Cloud |
| Microsoft Foundry | Batches, Models API, Files on Azure hosting | the US Data Zone type | Azure |

## Decision
- The Claude API, with Haiku 5.5; Northwind's requests carry `inference_geo="us"` (1.1x on price).
- If Northwind must buy through AWS: Claude Platform on AWS, the same code with `[platform] name = "aws"`.
- Not Bedrock, Google Cloud or Foundry for this workload: no Batches for the overnight volume, and on Bedrock
  generate itself breaks without structured outputs.

## Consequences
- One switch in config.toml; the factory builds the client; the tests cover every platform's class.
- Re-check `platforms.toml` when a platform's feature list changes; latency is measured from our own region with
  `experiments/latency.py` on each candidate before a move.

## Security and procurement
| Question | Answer | Source, read on |
|---|---|---|
| Who processes the data? | Anthropic (the Claude API); Anthropic on AWS infrastructure if we buy through AWS | Claude Platform on AWS, 2026-10-12 |
| Where is inference run? | The US only: `inference_geo="us"` on every Northwind request (NFR-5) | Data residency, 2026-10-12 |
| What do we send? | Lesson text and prompts only; no learner data (NFR-6, the data map from 8.2) | docs/requirements.md |
| How is access controlled? | One key per deployment and workspace; CI uses workload identity (8.5) | docs/deployments.md |
| How is it billed? | Anthropic directly; through the AWS bill on Claude Platform on AWS | Pricing, 2026-10-12 |
| What does it cost at our volume? | Within the quarter budget (NFR-4), held by `qf report` per feature | docs/budgets.md |

## Re-check
- 2027-01-12, or sooner when a platform's "Features not supported" list changes: re-read the five platform pages,
  update `quizforge/platforms.toml`, run `python -m quizforge.platforms`, and re-measure latency on any candidate.
- Each month: the deprecations page against `models.lock.toml` (docs/runbook.md).
