import asyncio
import json
import time
import tomllib
from dataclasses import replace
from datetime import datetime, timezone

import anthropic

from quizforge import retry, tracing, usage
from quizforge.client import make_client
from quizforge.config import ROOT
from quizforge.library import load_lesson
from quizforge.prompts import for_schema, load_prompt
from quizforge.repair import Refused, RepairFailed, write_checked
from quizforge.sanitize import clean
from quizforge.security import keys

ROUTE = tomllib.loads((ROOT / "config.toml").read_text())["route"]["generate"]  # measured in L7.6


class OverLimit(Exception):
    """The request could cost more than max_request_usd: it isn't sent."""


def user_turn(lesson_id: str, text: str, questions: int) -> str:
    """The lesson is data: cleaned, inside its own tags, with the ask after it."""
    return f'<lesson id="{lesson_id}">\n{clean(text)}\n</lesson>\n\nWrite {questions} questions.'


def cached_turn(lesson_id: str, text: str, questions: int) -> list:
    """The user turn as two blocks: the lesson, the same in every request and every repair (cached), then the ask."""
    lesson, ask = user_turn(lesson_id, text, questions).rsplit("\n\n", 1)
    return [{"type": "text", "text": lesson, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": ask}]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record(cfg, prices, label, message, counted, seconds):
    return usage.log(
        cfg.usage_log,
        time=_now(),
        label=label,
        model=cfg.model,
        request_id=getattr(message, "_request_id", None),
        counted=counted,
        input=message.usage.input_tokens,
        cache_write=message.usage.cache_creation_input_tokens or 0,
        cache_read=message.usage.cache_read_input_tokens or 0,
        output=message.usage.output_tokens,
        cost=usage.cost(prices, cfg.model, message.usage),
        seconds=round(seconds, 2),
    )


@tracing.traced
def generate_one(cfg, prices, lesson_id, version=None, client=None, out=print, route=None):
    """One lesson: the locked prompt version, the cleaned lesson, a schema-checked reply, repairs with a limit.

    Every attempt is cost-checked before it's sent and logged after. A lesson that passes is saved to
    output_dir; one that's refused, over the limit or still failing after the last retry goes to rejected_dir.
    """
    version = version or cfg.prompt
    route = route or ROUTE  # model, effort and max_tokens for generate
    cfg = replace(cfg, model=route["model"], max_tokens=route["max_tokens"])
    system = for_schema(load_prompt(cfg.prompts, version))
    lesson = clean(load_lesson(cfg.library, lesson_id))
    client = client or make_client().with_options(**retry.policy("generate"), middleware=[tracing.http_span])
    client = tracing.Traced(client)
    rows, counted = [], {}

    def before(messages):
        counted["last"] = client.messages.count_tokens(model=cfg.model, system=system, messages=messages).input_tokens
        most = usage.worst_case(prices, cfg.model, counted["last"], cfg.max_tokens)
        if most > cfg.max_request_usd:
            raise OverLimit(f"could cost ${most:.4f}, over the ${cfg.max_request_usd} limit")

    def after(attempt, message, seconds):
        rows.append(_record(cfg, prices, f"{lesson_id} {version} attempt {attempt}", message, counted["last"], seconds))

    result = {"lesson": lesson_id, "prompt": version, "model": cfg.model}
    try:
        data, attempts = write_checked(
            client,
            cfg.model,
            system,
            cached_turn(lesson_id, lesson, cfg.questions),
            lesson,
            cfg.questions,
            retries=cfg.retries,
            max_tokens=cfg.max_tokens,
            out=lambda line: out(f"{lesson_id:5} {line.strip()}"),
            before=before,
            after=after,
            checked=tracing.validated,
            effort=route.get("effort"),
        )
        data = keys.place(data, seed=lesson_id)  # the answer letter is code's choice, not the model's
        result.update(status="passed", attempts=attempts, questions=data.model_dump()["questions"])
    except RepairFailed as error:
        result.update(
            status="rejected", attempts=len(rows), problems=error.found or [str(error)], last_reply=error.text
        )
    except Refused as error:
        result.update(status="refused", attempts=len(rows), problems=[str(error)], decision="fallback")
    except anthropic.APIError as error:  # the SDK's retries are spent, or retrying can't help
        decision = retry.classify(error)
        result.update(status="error", attempts=len(rows), problems=[str(error)], decision=decision.action)
    except OverLimit as error:
        result.update(status="over limit", attempts=len(rows), problems=[str(error)])
    result["cost"] = round(sum(row["cost"] for row in rows), 6)
    result["path"] = str(_save(cfg, result))
    return result


async def generate_many(cfg, prices, lesson_ids, version=None, out=print):
    """Several lessons at once, at most cfg.concurrency in flight. The repair loop is a plain loop,
    so each lesson runs in a worker thread; the client is shared (it's safe across threads)."""
    client = make_client()
    limit = asyncio.Semaphore(cfg.concurrency)
    start = time.perf_counter()

    async def one(lesson_id):
        async with limit:
            out(f"{time.perf_counter() - start:6.2f} s  start  {lesson_id}")
            result = await asyncio.to_thread(generate_one, cfg, prices, lesson_id, version, client, out)
            out(
                f"{time.perf_counter() - start:6.2f} s  {result['status']:6} {lesson_id}  "
                f"{result['attempts']} attempt(s)  ${result['cost']:.5f}"
            )
            return result

    results = await asyncio.gather(*(one(lesson_id) for lesson_id in lesson_ids))
    return results, time.perf_counter() - start


def _save(cfg, result):
    """Passed items and rejected ones go to different folders; a new result replaces the lesson's old one."""
    keep, drop = (
        (cfg.output_dir, cfg.rejected_dir) if result["status"] == "passed" else (cfg.rejected_dir, cfg.output_dir)
    )
    keep.mkdir(parents=True, exist_ok=True)
    (drop / f"{result['lesson']}.json").unlink(missing_ok=True)
    path = keep / f"{result['lesson']}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
