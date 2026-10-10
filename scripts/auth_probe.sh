#!/bin/bash
# Knock on the library server's HTTP door four ways. The token is read from its file, never printed.
URL=http://127.0.0.1:8765/mcp
TOKEN=$(cat ~/.config/quiz-forge/mcp-token)
JSON=(-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream")
DISCOVER=(-H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: server/discover" -d '{"jsonrpc": "2.0",
  "id": 1, "method": "server/discover", "params": {"_meta": {"io.modelcontextprotocol/protocolVersion":
  "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}}}')

echo "== 1. no token"
curl -si "$URL" "${JSON[@]}" "${DISCOVER[@]}" | grep -iE "^HTTP|^www-authenticate"
echo "== 2. the metadata that 401 points to"
curl -s http://127.0.0.1:8765/.well-known/oauth-protected-resource/mcp; echo
echo "== 3. with the token"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$URL" "${JSON[@]}" -H "Authorization: Bearer $TOKEN" "${DISCOVER[@]}"
echo "== 4. with the token, from another host name (DNS rebinding)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$URL" "${JSON[@]}" -H "Host: evil.example:8765" \
  -H "Authorization: Bearer $TOKEN" "${DISCOVER[@]}"
