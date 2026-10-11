"""A local stand-in for the Messages API: it answers each request with the next status in a script.
Only for tests and demos. It listens on 127.0.0.1 and never reads or prints the request's headers."""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

ERRORS = {400: "invalid_request_error", 401: "authentication_error", 404: "not_found_error",
          413: "request_too_large", 429: "rate_limit_error", 500: "api_error", 529: "overloaded_error"}
REPLY = {"id": "msg_mock", "type": "message", "role": "assistant", "model": "claude-haiku-4-5",
         "content": [{"type": "text", "text": "Hello from the mock."}], "stop_reason": "end_turn",
         "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 6}}


def answer(step):
    """'429:2' -> (429, headers, body); 'spendcap', 'refusal', 'slow:30' and plain statuses too."""
    name, _, arg = step.partition(":")
    if name == "200":
        return 200, {}, REPLY
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


def serve(script, port=8787):
    seen = []  # arrival times, counted from the first request

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["content-length"]))
            seen.append(time.time())
            n = len(seen)
            step = script[min(n, len(script)) - 1]  # the last step repeats
            print(f"mock    {seen[-1] - seen[0]:5.1f} s  request {n} -> {step}", flush=True)
            status, headers, body = answer(step)
            data = json.dumps(body).encode()
            self.send_response(status)
            for key, value in {**headers, "request-id": f"req_mock_{n}", "content-type": "application/json"}.items():
                self.send_header(key, value)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):  # no access log: it would print every request line
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    serve(sys.argv[1:] or ["200"])
    print("mock API on http://127.0.0.1:8787 (Ctrl+C to stop)", flush=True)
    while True:
        time.sleep(3600)
