"""What to do about a failure. The SDK already retried the transient ones; this decides what happens next."""
import tomllib
from dataclasses import dataclass

import anthropic

from quizforge.config import ROOT


@dataclass(frozen=True)
class Decision:
    action: str  # wait | stop | fix | fallback | continue | done
    reason: str


def policy(feature):
    """Retry settings per feature, from config.toml [retry.<feature>]: max_retries and timeout (seconds)."""
    return tomllib.loads((ROOT / "config.toml").read_text())["retry"][feature]


def classify(failure, budget=None):
    """An SDK exception or a Message -> a Decision. budget: the seconds this feature can wait."""
    if isinstance(failure, anthropic.APIConnectionError):  # includes timeouts
        return Decision("wait", "no response: the SDK retried; re-queue it later")
    if isinstance(failure, anthropic.APIStatusError):
        status, body = failure.status_code, failure.body if isinstance(failure.body, dict) else {}
        error = body.get("error", {})
        if (error.get("details") or {}).get("error_code") == "enforced_spend_limit_reached":
            return Decision("stop", "spend cap reached: no retry can succeed until access resumes")
        if status == 400 and error.get("message", "").startswith("You have reached your specified API usage limits"):
            return Decision("stop", "your own spend limit: raise it or wait")
        if status in (401, 402, 403):
            return Decision("stop", f"{status}: credentials, billing or permission; tell a person")
        if status in (408, 409, 429) or status >= 500:
            wait = failure.response.headers.get("retry-after")
            if budget is not None and wait and float(wait) > budget:
                return Decision("wait", f"retry-after {wait} s is over this feature's {budget} s budget: re-queue it")
            return Decision("wait", f"{status} after the SDK's retries: re-queue it later")
        return Decision("fix", f"{status}: the request itself is wrong; fix the code or shrink the input")
    if getattr(failure, "stop_reason", None) == "refusal":
        return Decision("fallback", "a refusal is a 200: another model or a person, not the same request")
    if getattr(failure, "stop_reason", None) == "max_tokens":
        return Decision("continue", "cut off at max_tokens: raise the cap or continue the reply")
    return Decision("done", "a normal reply")
