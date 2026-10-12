"""The client contract, written before the refactor: what each path's client must keep. No request is sent."""
import asyncio

import pytest

from quizforge import generate, tracing
from quizforge.client import make_client
from quizforge.config import load_config


@pytest.fixture(autouse=True)
def dummy_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


def keeps_generate_policy(client):
    return client.max_retries == 4 and client.timeout == 120 and tracing.http_span in client.middleware


class Caught(Exception):
    """Stops generate_one where its client is ready, before any request."""


def test_one_lesson_gets_the_generate_policy(monkeypatch):
    def catch(client):
        raise Caught(client)

    monkeypatch.setattr(tracing, "Traced", catch)
    with pytest.raises(Caught) as stopped:
        generate.generate_one(load_config(), {}, "L1.3")
    assert keeps_generate_policy(stopped.value.args[0])


def test_many_lessons_get_the_generate_policy(monkeypatch):
    seen = []
    done = {"status": "passed", "attempts": 1, "cost": 0.0}
    monkeypatch.setattr(generate, "generate_one", lambda *a, **k: seen.append(a[4]) or done)
    asyncio.run(generate.generate_many(load_config(), {}, ["L1.3", "L2.1"], out=lambda line: None))
    assert all(keeps_generate_policy(client) for client in seen)


def test_other_features_keep_the_sdk_defaults():
    client = make_client()
    assert client.max_retries == 2 and client.timeout.read == 600


def test_the_base_url_still_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:8787")
    assert str(make_client().base_url).startswith("http://127.0.0.1:8787")
