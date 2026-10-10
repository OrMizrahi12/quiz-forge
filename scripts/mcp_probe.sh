#!/bin/bash
# Open a conversation with an MCP server over Streamable HTTP, the 2025 way and the 2026 way.
URL=${1:-http://127.0.0.1:8765/mcp}
SHOW='^HTTP/1.1 [0-9]+|^mcp-session-id: [0-9a-f]+|"(protocolVersion|supportedVersions)":[^,]+'

echo "== 2025-11-25: an initialize handshake, then a session"
curl -s -D - "$URL" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25",
       "capabilities": {}, "clientInfo": {"name": "probe", "version": "1"}}}' | grep -ioE "$SHOW"

echo "== 2026-07-28: server/discover; every request carries its own version"
curl -s -D - "$URL" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: server/discover" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": {
       "io.modelcontextprotocol/protocolVersion": "2026-07-28",
       "io.modelcontextprotocol/clientCapabilities": {}}}}' | grep -ioE "$SHOW"
