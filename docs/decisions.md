# Decisions

## 1. generate stays a workflow (Lesson 4.1)

The job: 2 checked questions per lesson, for every lesson, again and again.

- Complexity: low. The steps are known before we start: write, check in code, repair.
- Value: low per item. One question is worth cents, and we write many.
- Viability: Haiku 4.5 does the job either way.
- Cost of error: a wrong quote misleads a student; our code checks catch it either way.

Measured on L1.3, 3 runs each (experiments/workflow_vs_agent.py):
- workflow: 1.3 requests, 7,221 input tokens, $0.0105 per run
- agent: 4.0 requests, 20,958 input tokens, $0.0261 per run

Decision: generate stays a workflow. An agent is for a job whose steps we can't list in advance.
