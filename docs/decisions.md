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


## 2. Tools, Skills and MCP: one decision per need (Lesson 6.4)

The rule, asked in this order:
- Anthropic already ships it, and where it runs doesn't matter: a built-in tool.
- What's missing is knowledge or a procedure, not a connection: a Skill.
- Several hosts need it, or it needs its own process, credentials or rights: MCP.
- One app needs our code inside its own loop: a custom tool.

Context each one adds to a request, on Haiku 4.5 (experiments/tool_choice.py):
custom tool +767, MCP 3 tools +878, web fetch +1021, Skill +44 (+440 when used).

| Need | Choice | Deciding constraint | What we give up |
|---|---|---|---|
| Check a quote while generate writes | custom tool | one app, its own loop | other hosts can't call it |
| Search the library from Claude Code, CI, apps | MCP server | many hosts, one code path | a process to run and secure |
| Read a public docs page | built-in web fetch | nothing to host | less control over what is fetched |
| How to write and judge an item | Skill | knowledge, loaded on demand | a host that loads Skills |

check_quote keeps two forms on purpose: one function (quizforge/sources.py) behind
the custom tool and the MCP tool.
