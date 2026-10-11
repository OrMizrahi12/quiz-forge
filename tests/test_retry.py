from types import SimpleNamespace

import anthropic
import httpx2

from quizforge.retry import classify, policy

URL = "http://127.0.0.1:8787/v1/messages"


def error(status, body=None, headers=None):
    """An SDK error as the SDK builds it from a response: no network, no key."""
    response = httpx2.Response(status, headers=headers, request=httpx2.Request("POST", URL))
    return anthropic.APIStatusError("mock", response=response, body=body or {})


def test_transient_errors_wait():
    assert classify(error(529)).action == "wait"
    assert classify(error(429, headers={"retry-after": "2"})).action == "wait"
    assert classify(anthropic.APITimeoutError(httpx2.Request("POST", URL))).action == "wait"


def test_terminal_errors_stop_or_fix():
    cap = {"error": {"type": "rate_limit_error", "details": {"error_code": "enforced_spend_limit_reached"}}}
    assert classify(error(429, cap)).action == "stop"
    assert classify(error(401)).action == "stop"
    assert [classify(error(s)).action for s in (400, 404, 413)] == ["fix"] * 3


def test_a_long_retry_after_is_over_the_budget():
    decision = classify(error(429, headers={"retry-after": "120"}), budget=20)
    assert decision.action == "wait" and "budget" in decision.reason


def test_normal_replies_that_still_failed():
    assert classify(SimpleNamespace(stop_reason="refusal")).action == "fallback"
    assert classify(SimpleNamespace(stop_reason="max_tokens")).action == "continue"


def test_policies_per_feature():
    assert policy("check")["max_retries"] < policy("generate")["max_retries"]
