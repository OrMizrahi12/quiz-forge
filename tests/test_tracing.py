"""Spans in memory: one generate run with a scripted client produces the job, call and validate spans."""
from types import SimpleNamespace

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from quizforge import tracing
from tests.test_generate import BASE, Fake, real_sentence, reply, run


@pytest.fixture
def spans(monkeypatch):
    exporter, provider = InMemorySpanExporter(), TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "tracer", provider.get_tracer("test"))
    return exporter


def test_a_repaired_run_is_one_tree(tmp_path, spans):
    run(tmp_path, Fake(reply("not in the lesson at all, not one bit"), reply(real_sentence())))
    done = spans.get_finished_spans()  # a span is finished when it ends: the job last
    chat = f"chat {BASE.model}"
    assert [span.name for span in done] == [chat, "validate", chat, "validate", "generate L1.3"]
    assert all(span.parent.span_id == done[-1].context.span_id for span in done[:-1])
    assert done[1].attributes["quizforge.problems"] > 0 and not done[1].status.is_ok


def test_input_tokens_include_the_cache(spans):
    used = SimpleNamespace(input_tokens=100, output_tokens=5, cache_read_input_tokens=4000,
                           cache_creation_input_tokens=0)
    message = SimpleNamespace(stop_reason="end_turn", usage=used)
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **request: message))
    tracing.Traced(client).create(model="claude-haiku-4-5", max_tokens=10, messages=[])
    chat = spans.get_finished_spans()[0]
    assert chat.attributes["gen_ai.usage.input_tokens"] == 4100
    assert chat.attributes["gen_ai.response.finish_reasons"] == ("end_turn",)
