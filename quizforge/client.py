import anthropic
from dotenv import load_dotenv

from quizforge import retry, tracing
from quizforge import platforms
from quizforge.config import ROOT

# Claude 4.5 models and earlier accept the partial reply as the start of the assistant turn (prefill).
# Newer models reject prefill, so they get the partial reply inside a user message instead (streaming docs).
PREFILL_OK = ("claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5")
DROPS = (anthropic.APIConnectionError, ConnectionError)  # a connection that breaks partway through a stream


def make_client(feature=None, asynchronous=False):
    """The one place client options are set: the feature's [retry.<feature>] policy, if any, and tracing."""
    load_dotenv(ROOT / ".env")  # this deployment's own key (QF_HOME/.env); the key is never printed
    client = platforms.base_client(asynchronous)
    return client.with_options(**(retry.policy_or_none(feature) or {}), middleware=[tracing.http_span])


def continuation(model: str, messages: list, partial: str) -> list:
    """The messages for a request that picks up a broken stream where its text stopped."""
    partial = partial.rstrip()  # the API rejects a final assistant turn that ends in whitespace
    if model.startswith(PREFILL_OK):
        return messages + [{"role": "assistant", "content": partial}]
    return messages + [
        {
            "role": "user",
            "content": "Your previous response was interrupted and ended with "
            f"{partial}. Continue from where you left off.",
        }
    ]


def stream_reply(client, *, model, system, messages, max_tokens, on_text=lambda text: None, max_resumes=2):
    """Stream one reply; if the connection drops partway, keep the text and resume.

    Returns (text, finals): the whole text, and (final Message, request id) for each request that finished.
    A broken request has no final message, so its partial usage can't be read here.
    """
    text, finals, request = "", [], messages
    for attempt in range(max_resumes + 1):
        try:
            with client.messages.stream(model=model, max_tokens=max_tokens, system=system, messages=request) as stream:
                for chunk in stream.text_stream:
                    text += chunk
                    on_text(chunk)
                finals.append((stream.get_final_message(), stream.request_id))
            return text, finals
        except DROPS:
            if attempt == max_resumes:
                raise
            on_text(f"\n--- stream broke after {len(text)} characters; resuming ---\n")
            request = continuation(model, messages, text)
