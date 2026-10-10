# Scope for a security review: Claude and a legacy system
Hypothetical customer: a regulated bank (invented). A starting frame for a real review, not legal advice.

## Goal and non-goals
- Goal: Claude Code helps modernize a legacy codebase: analysis, tests, refactors.
- Goal: Claude reaches one internal system (the policy library) through MCP, read-only.
- Not in scope: production data, production deploys, any write tool.

## Data
- What leaves the network: prompts, code excerpts and tool results, sent to the API.
- Check ZDR eligibility per feature. The MCP connector and MCP tunnels are not covered.

## Identities
- People: company SSO. Workloads: workload identity federation, no static API keys.
- MCP over HTTP: an OAuth resource server. Tokens name this server (audience).
- No token passthrough: the server never forwards a user's token downstream.
- Scopes per tool: library:read now; a write scope only after its own review.

## Network path
- stdio inside the dev environment, or HTTP bound to internal hosts with Host/Origin checks.
- Hosted Claude features reach inside through an outbound-only tunnel, never an open port.
- Proxy, custom CA and mTLS as the network team requires.

## Least privilege and change control
- Managed MCP: an allowlist of approved servers. Permission rules per tool.
- Pinned versions of servers, plugins and their tool lists; review before each upgrade.

## Human gates and audit
- Plan mode and edit review; a person merges every PR; nothing deploys on its own.
- Logged: request IDs, tool calls, who approved what. Traces to the customer's monitoring.

## Quiz Forge's library server, today and before production
| | Today | Before production |
|---|---|---|
| Identity | dev token, hash on disk | tokens from the IdP, audience checked |
| Path | 127.0.0.1 only | internal host or an outbound tunnel |
| Rights | 3 read-only tools | the same, allowlisted in managed MCP |

## Exit criteria and open risks
- Exit: the reviewer signs off on each section above, with evidence.
- Open: prompt injection through tool results (Module 8); the customer's own policy decides.
