"""OpenTelemetry for Quiz Forge: a span per job, per Claude call and per HTTP attempt, written to runs/traces/.
Spans hold ids, models, statuses and token counts: never a prompt, a reply or a key."""
import functools
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

from quizforge.config import ROOT

tracer = trace.get_tracer("quizforge")  # does nothing until setup() runs: tests and other commands pay nothing


def setup(folder=ROOT / "runs/traces"):
    """One file per run. In production you'd export with OTLP to a collector instead."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.jsonl"
    exporter = ConsoleSpanExporter(out=open(path, "a"), formatter=lambda span: span.to_json(indent=None) + "\n")
    provider = TracerProvider(resource=Resource.create({"service.name": "quiz-forge"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return path


def http_span(request, call_next):
    """SDK middleware: it runs once per HTTP attempt, retries included."""
    with tracer.start_as_current_span(f"{request.method.upper()} {request.url}", kind=SpanKind.CLIENT) as span:
        span.set_attribute("quizforge.attempt", request.retries_taken + 1)
        response = call_next(request)
        span.set_attribute("http.response.status_code", response.status_code)
        span.set_attribute("anthropic.request_id", response.request_id or "")
        if response.status_code >= 400:
            span.set_attribute("error.type", str(response.status_code))
            span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
        return response


class Traced:
    """Wraps a client: each messages.create runs in a 'chat <model>' span with the GenAI attributes."""

    def __init__(self, client):
        self.client, self.messages = client, self

    def count_tokens(self, **request):
        return self.client.messages.count_tokens(**request)

    def create(self, **request):
        with tracer.start_as_current_span(f"chat {request['model']}") as span:
            message = self.client.messages.create(**request)
            used = message.usage
            read, written = used.cache_read_input_tokens or 0, used.cache_creation_input_tokens or 0
            span.set_attributes({
                "gen_ai.provider.name": "anthropic",
                "gen_ai.request.model": request["model"],
                "gen_ai.response.finish_reasons": [message.stop_reason],
                "gen_ai.usage.input_tokens": used.input_tokens + read + written,  # the API's count leaves cache out
                "gen_ai.usage.cache_read.input_tokens": read,
                "gen_ai.usage.output_tokens": used.output_tokens,
            })
            if message.stop_reason in ("refusal", "max_tokens"):
                span.add_event(message.stop_reason)  # the call worked; the output didn't
            return message


def validated(attempt, found):
    """The code checks on one reply: a span with the number of problems, ERROR with the first one."""
    with tracer.start_as_current_span("validate") as span:
        span.set_attribute("quizforge.problems", len(found))
        if found:
            span.set_status(Status(StatusCode.ERROR, found[0]))


def traced(job):
    """A span around one job for one lesson: generate_one -> 'generate L1.3', with its outcome."""

    @functools.wraps(job)
    def run(cfg, prices, lesson_id, *args, **kwargs):
        with tracer.start_as_current_span(f"{job.__name__.split('_')[0]} {lesson_id}") as span:
            result = job(cfg, prices, lesson_id, *args, **kwargs)
            span.set_attribute("quizforge.status", result["status"])
            span.set_attribute("quizforge.decision", result.get("decision", ""))
            if result["status"] != "passed":
                span.set_status(Status(StatusCode.ERROR, result["problems"][0]))
            return result

    return run
