"""A local stand-in for the Messages API: it answers each request with the next status in a script.
Only for tests and demos. It listens on 127.0.0.1 and never reads or prints the request's headers."""
import json
import math
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread

ERRORS = {400: "invalid_request_error", 401: "authentication_error", 404: "not_found_error",
          413: "request_too_large", 429: "rate_limit_error", 500: "api_error", 529: "overloaded_error"}
REPLY = {"id": "msg_mock", "type": "message", "role": "assistant", "model": "claude-haiku-4-5",
         "content": [{"type": "text", "text": "Hello from the mock."}], "stop_reason": "end_turn",
         "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 6}}


def answer(step):
    """'429:2' -> (429, headers, body); 'tokens', 'reply:FILE', 'spendcap', 'refusal', 'slow:30', plain statuses."""
    name, _, arg = step.partition(":")
    if name == "200":
        return 200, {}, REPLY
    if name == "tokens":  # a count_tokens answer
        return 200, {}, {"input_tokens": 1500}
    if name == "reply":  # a saved reply, read from a file: what the model said once
        return 200, {}, {**REPLY, "content": [{"type": "text", "text": Path(arg).read_text()}]}
    if name == "refusal":
        return 200, {}, {**REPLY, "content": [], "stop_reason": "refusal"}
    if name == "slow":
        time.sleep(float(arg))
        return 200, {}, REPLY
    if name == "spendcap":  # the tier's monthly cap: no retry-after
        error = {"type": "rate_limit_error", "message": "Spend cap reached.",
                 "details": {"error_code": "enforced_spend_limit_reached"}}
        return 429, {}, {"type": "error", "error": error}
    status = int(name)
    headers = {"retry-after": arg} if arg else {}
    return status, headers, {"type": "error", "error": {"type": ERRORS.get(status, "api_error"), "message": "mock"}}


class Bucket:
    """A rate limit as a token bucket: it refills continuously at rpm / 60 per second and holds one second's worth;
    a request that finds it empty gets a 429 with the seconds until a token is back."""

    def __init__(self, rpm):
        self.rate = self.size = self.tokens = rpm / 60
        self.at, self.lock = time.time(), Lock()

    def take(self):
        with self.lock:
            now = time.time()
            self.tokens, self.at = min(self.size, self.tokens + (now - self.at) * self.rate), now
            if self.tokens >= 1:
                self.tokens -= 1
                return 0
            return (1 - self.tokens) / self.rate


def serve(script, port=8787, rpm=0, latency=(0.0, 0.0), quiet=False):
    seen, statuses = [], []  # arrival times (counted from the first request), and every status sent
    bucket = Bucket(rpm) if rpm else None

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["content-length"]))
            seen.append(time.time())
            n = len(seen)
            wait = bucket.take() if bucket else 0
            step = f"429:{math.ceil(wait)}" if wait else script[min(n, len(script)) - 1]  # the last step repeats
            if not quiet:
                print(f"mock    {seen[-1] - seen[0]:5.1f} s  request {n} -> {step}", flush=True)
            if step == "200" and latency[0]:
                time.sleep(max(0.05, random.gauss(*latency)))  # a reply takes time: mean, jitter
            status, headers, body = answer(step)
            statuses.append(status)
            data = json.dumps(body).encode()
            self.send_response(status)
            for key, value in {**headers, "request-id": f"req_mock_{n}", "content-type": "application/json"}.items():
                self.send_header(key, value)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # the Models API: the model asked for, active
            body = {"type": "model", "id": self.path.rsplit("/", 1)[-1], "display_name": "mock",
                    "created_at": "2026-01-01T00:00:00Z", "lifecycle": "active", "retires_at": None}
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):  # no access log: it would print every request line
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.statuses = statuses
    Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    serve(sys.argv[1:] or ["200"])
    print("mock API on http://127.0.0.1:8787 (Ctrl+C to stop)", flush=True)
    while True:
        time.sleep(3600)
