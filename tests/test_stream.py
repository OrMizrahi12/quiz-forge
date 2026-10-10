from types import SimpleNamespace

import pytest

from quizforge.client import continuation, stream_reply

ASK = [{"role": "user", "content": "Write one question."}]


class FakeStream:
    """Stands in for client.messages.stream(): yields chunks, and can drop the connection partway."""

    def __init__(self, chunks, drop_after=None):
        self.chunks, self.drop_after, self.request_id = chunks, drop_after, "req_fake"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        for i, chunk in enumerate(self.chunks):
            if self.drop_after is not None and i == self.drop_after:
                raise ConnectionError("the network dropped")
            yield chunk

    def get_final_message(self):
        return SimpleNamespace(
            stop_reason="end_turn", usage=SimpleNamespace(input_tokens=10, output_tokens=len(self.chunks))
        )


class FakeClient:
    def __init__(self, *streams):
        self.streams, self.requests = list(streams), []
        self.messages = SimpleNamespace(stream=self._stream)

    def _stream(self, **request):
        self.requests.append(request)
        return self.streams.pop(0)


def test_a_whole_stream_comes_back_in_one_request():
    client = FakeClient(FakeStream(["What ", "is ", "DNS?"]))
    text, finals = stream_reply(client, model="claude-haiku-4-5-20251001", system="s", messages=ASK, max_tokens=50)
    assert text == "What is DNS?" and len(finals) == 1 and len(client.requests) == 1


def test_a_broken_stream_keeps_its_text_and_resumes():
    client = FakeClient(
        FakeStream(["Question: What ", "does DNS ", "do? "], drop_after=2), FakeStream(["A) ...", " Answer: A"])
    )
    text, finals = stream_reply(client, model="claude-haiku-4-5-20251001", system="s", messages=ASK, max_tokens=50)
    assert text == "Question: What does DNS A) ... Answer: A"
    assert len(finals) == 1  # only the request that finished has a final message
    resumed = client.requests[1]["messages"]
    assert resumed[-1] == {
        "role": "assistant",
        "content": "Question: What does DNS",
    }  # the partial, trailing space removed


def test_resuming_gives_up_after_the_limit():
    client = FakeClient(*(FakeStream(["a", "b"], drop_after=1) for _ in range(3)))
    with pytest.raises(ConnectionError):
        stream_reply(client, model="claude-haiku-4-5-20251001", system="s", messages=ASK, max_tokens=50, max_resumes=2)
    assert len(client.requests) == 3


def test_newer_models_get_the_partial_in_a_user_message():
    msgs = continuation("claude-haiku-5-5", ASK, "Question: What does ")
    assert msgs[-1]["role"] == "user"
    assert "interrupted and ended with Question: What does. Continue from where you left off." in msgs[-1]["content"]


def test_continuation_never_changes_the_original_messages():
    original = [dict(m) for m in ASK]
    continuation("claude-haiku-4-5-20251001", ASK, "partial")
    assert ASK == original
