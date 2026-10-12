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
- Security and procurement: who processes the data (Anthropic, or Anthropic on AWS), where (US only), how access
  is controlled (keys or AWS IAM) and how it is billed.
