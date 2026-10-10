#!/bin/sh
# Claude Code's headersHelper: print the Authorization header on stdout, read fresh at every connection.
# It stands in for your company's SSO or secrets-manager command. Never run it by hand: its output is a secret.
printf '{"Authorization": "Bearer %s"}\n' "$(cat "$HOME/.config/quiz-forge/mcp-token")"
