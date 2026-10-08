import asyncio
import time
from datetime import datetime, timezone

from quizforge import usage
from quizforge.client import make_client, stream_reply
from quizforge.library import load_lesson

SYSTEM = "You write practice exam questions from course lesson notes. Use only facts stated in the lesson."


def ask(lesson_id: str, text: str, questions: int) -> list:
    return [{"role": "user", "content": f"Lesson {lesson_id}:\n\n{text}\n\nWrite {questions} multiple-choice practice "
             "questions about this lesson. For each one: the question, options A to D, the answer letter, and a "
             "one-line explanation that quotes the lesson."}]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _check_cost(cfg, prices, lesson_id, counted):
    most = usage.worst_case(prices, cfg.model, counted, cfg.max_tokens)
    if most > cfg.max_request_usd:
        raise SystemExit(f"{lesson_id}: could cost ${most:.4f}, over the ${cfg.max_request_usd} limit")


def _record(cfg, prices, label, message, request_id, counted, seconds):
    return usage.log(cfg.usage_log, time=_now(), label=label, model=cfg.model, request_id=request_id,
                     counted=counted, input=message.usage.input_tokens,
                     cache_write=message.usage.cache_creation_input_tokens or 0,
                     cache_read=message.usage.cache_read_input_tokens or 0,
                     output=message.usage.output_tokens, cost=usage.cost(prices, cfg.model, message.usage),
                     seconds=round(seconds, 2))


def generate_one(cfg, prices, lesson_id, out=print):
    """One lesson: count first, check the cost limit, stream the questions, log every request."""
    client = make_client()
    messages = ask(lesson_id, load_lesson(cfg.library, lesson_id), cfg.questions)
    counted = client.messages.count_tokens(model=cfg.model, system=SYSTEM, messages=messages).input_tokens
    _check_cost(cfg, prices, lesson_id, counted)
    start = time.perf_counter()
    text, finals = stream_reply(client, model=cfg.model, system=SYSTEM, messages=messages, max_tokens=cfg.max_tokens,
                                on_text=lambda chunk: out(chunk, end="", flush=True))
    seconds = time.perf_counter() - start
    rows = [_record(cfg, prices, f"{lesson_id} generate", m, request_id, counted, seconds) for m, request_id in finals]
    _save(cfg, lesson_id, text)
    return text, finals, rows


async def generate_many(cfg, prices, lesson_ids, out=print):
    """Several lessons at once: the async client, with at most cfg.concurrency calls in flight."""
    client = make_client(asynchronous=True)
    limit = asyncio.Semaphore(cfg.concurrency)
    start = time.perf_counter()

    async def one(lesson_id):
        async with limit:
            messages = ask(lesson_id, load_lesson(cfg.library, lesson_id), cfg.questions)
            counted = (await client.messages.count_tokens(model=cfg.model, system=SYSTEM, messages=messages)).input_tokens
            _check_cost(cfg, prices, lesson_id, counted)
            began = time.perf_counter()
            out(f"{began - start:6.2f} s  start  {lesson_id}")
            message = await client.messages.create(model=cfg.model, max_tokens=cfg.max_tokens, system=SYSTEM, messages=messages)
            row = _record(cfg, prices, f"{lesson_id} generate", message, message._request_id, counted, time.perf_counter() - began)
            _save(cfg, lesson_id, next(b.text for b in message.content if b.type == "text"))
            out(f"{time.perf_counter() - start:6.2f} s  done   {lesson_id}  {row['input']} in {row['output']} out "
                f"${row['cost']:.5f}  {message.stop_reason}")
            return row

    rows = await asyncio.gather(*(one(lesson_id) for lesson_id in lesson_ids))
    return rows, time.perf_counter() - start


def _save(cfg, lesson_id, text):
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.output_dir / f"{lesson_id}.md").write_text(text + "\n")
