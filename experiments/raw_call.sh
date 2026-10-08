curl -s https://api.anthropic.com/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d @"$1" \
  -D runs/headers.txt -o runs/reply.json -w "HTTP %{http_code}\n"
