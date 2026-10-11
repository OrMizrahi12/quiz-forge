"""One request to the local mock, with the SDK's own retry settings. Usage: retry_demo [--retries N] [--timeout S] STEP..."""
import argparse
import time

import anthropic

from experiments.mock_api import serve

parser = argparse.ArgumentParser()
parser.add_argument("--retries", type=int, default=2)  # the SDK's default
parser.add_argument("--timeout", type=float, default=600)  # the SDK's default: 10 minutes
parser.add_argument("script", nargs="+")
args = parser.parse_args()

serve(args.script)
client = anthropic.Anthropic(base_url="http://127.0.0.1:8787", api_key="mock-not-a-real-key",
                             max_retries=args.retries, timeout=args.timeout)
start = time.time()
try:
    reply = client.messages.create(model="claude-haiku-4-5", max_tokens=50,
                                   messages=[{"role": "user", "content": "Hi"}])
    print(f"client  {time.time() - start:5.1f} s  200, stop_reason {reply.stop_reason}, {reply._request_id}")
except anthropic.APIStatusError as error:
    detail = error.body.get("error", {}).get("details") or ""
    print(f"client  {time.time() - start:5.1f} s  {type(error).__name__} {error.status_code}, {error.request_id} {detail}")
except anthropic.APIConnectionError as error:
    print(f"client  {time.time() - start:5.1f} s  {type(error).__name__}")
