"""Many lessons as one Message Batch: half the price, results within 24 hours.

A batch has no back and forth, so a reply that fails the checks gets its repairs afterwards, through the
realtime repair loop, starting from the batch's own reply.
"""
import json

from pydantic import ValidationError

from quizforge import usage
from quizforge.config import ROOT
from quizforge.generate import OverLimit, _now, _save, generate_one, user_turn
from quizforge.library import load_lesson
from quizforge.prompts import for_schema, load_prompt
from quizforge.repair import FORMAT, Refused, RepairFailed, write_checked
from quizforge.sanitize import clean
from quizforge.schema import Questions
from quizforge.validate import problems

SENT = ROOT / "runs" / "batches.jsonl"   # one line per batch we submitted


def custom_id(lesson_id, version):
    """Letters, digits, - and _ only, up to 64: L3.2 with v4 -> L3_2-v4."""
    return f"{lesson_id.replace('.', '_')}-{version}"


def lesson_of(cid):
    return cid.split("-")[0].replace("_", ".")


def version_of(cid):
    return cid.split("-", 1)[1]


def requests(cfg, lesson_ids, version=None):
    """One request per lesson: generate_one's first request, with no repairs."""
    version = version or cfg.prompt
    system = for_schema(load_prompt(cfg.prompts, version))
    for lesson_id in lesson_ids:
        lesson = clean(load_lesson(cfg.library, lesson_id))
        ask = user_turn(lesson_id, lesson, cfg.questions)
        params = {"model": cfg.model, "max_tokens": cfg.max_tokens,
                  "system": system, "output_config": FORMAT,
                  "messages": [{"role": "user", "content": ask}]}
        yield {"custom_id": custom_id(lesson_id, version), "params": params}


def submit(client, reqs):
    batch = client.messages.batches.create(requests=reqs)
    SENT.parent.mkdir(exist_ok=True)
    with open(SENT, "a") as f:
        sent = {"id": batch.id, "requests": [r["custom_id"] for r in reqs]}
        f.write(json.dumps(sent) + "\n")
    return batch


def last_sent():
    if not SENT.exists():
        raise SystemExit("no batch submitted yet: run batch submit first")
    return json.loads(SENT.read_text().splitlines()[-1])


def collect(client, cfg, batch_id):
    """Each result, matched to its lesson by custom_id (never by position), then checked in code.

    Yields (custom_id, outcome, found, text, usage): outcome is the result type; found lists the problems.
    """
    for result in client.messages.batches.results(batch_id):
        cid, outcome = result.custom_id, result.result
        if outcome.type != "succeeded":
            why = outcome.error.error.type if outcome.type == "errored" else outcome.type
            yield cid, outcome.type, [why], "", None
            continue
        reply = outcome.message
        lesson = clean(load_lesson(cfg.library, lesson_of(cid)))
        text = reply.content[0].text if reply.content else ""
        if reply.stop_reason != "end_turn":
            found = [f"stop_reason {reply.stop_reason}"]
        else:
            try:
                found = problems(Questions.model_validate_json(text), lesson, cfg.questions)
            except ValidationError as error:
                found = [f"not valid against the schema: {error.errors()[0]['type']}"]
        yield cid, "succeeded", found, text, reply.usage


def finish(cfg, prices, client, cid, outcome, found, text, used, out=print):
    """One batch result to a saved result: passed as is; a failing reply repaired in realtime, from the batch
    reply on; a request the batch couldn't run sent again in realtime, from the start."""
    lesson_id, version = lesson_of(cid), version_of(cid)
    batch_cost = usage.cost(prices, cfg.model, used) / 2 if used else 0.0   # the batch price: half, on every token
    if used:
        usage.log(cfg.usage_log, time=_now(), label=f"{lesson_id} {version} batch", model=cfg.model, request_id=None,
                  counted=None, input=used.input_tokens, cache_write=used.cache_creation_input_tokens or 0,
                  cache_read=used.cache_read_input_tokens or 0, output=used.output_tokens, cost=round(batch_cost, 6), seconds=None)
    if outcome in ("expired", "canceled"):
        out(f"{lesson_id:5} {outcome} in the batch: sent again in realtime")
        result = generate_one(cfg, prices, lesson_id, version, client, out)
        result["via"] = f"{outcome}, then realtime"
        return result
    result = {"lesson": lesson_id, "prompt": version, "model": cfg.model, "via": "batch"}
    if outcome == "errored":
        result.update(status="errored", attempts=1, problems=found)
    elif not found:
        result.update(status="passed", attempts=1, questions=Questions.model_validate_json(text).model_dump()["questions"])
    else:
        result.update(_repair(cfg, prices, client, lesson_id, version, text, found, out))
    result["cost"] = round(batch_cost + result.pop("repair_cost", 0.0), 6)
    result["path"] = str(_save(cfg, result))
    return result


def _repair(cfg, prices, client, lesson_id, version, text, found, out):
    """The second pass: the batch reply and its problems become attempt 1 of the realtime repair loop."""
    system = for_schema(load_prompt(cfg.prompts, version))
    lesson = clean(load_lesson(cfg.library, lesson_id))
    ask = user_turn(lesson_id, lesson, cfg.questions)
    fix = "Fix these problems, and keep everything else:\n- " + "\n- ".join(found)
    history = [{"role": "user", "content": ask}, {"role": "assistant", "content": text}, {"role": "user", "content": fix}]
    spent, counted = [], {}

    def before(messages):
        counted["last"] = client.messages.count_tokens(model=cfg.model, system=system, messages=messages).input_tokens
        if usage.worst_case(prices, cfg.model, counted["last"], cfg.max_tokens) > cfg.max_request_usd:
            raise OverLimit("the repair could cost more than max_request_usd")

    def after(attempt, message, seconds):
        cost = usage.cost(prices, cfg.model, message.usage)
        spent.append(cost)
        usage.log(cfg.usage_log, time=_now(), label=f"{lesson_id} {version} attempt {attempt}", model=cfg.model,
                  request_id=getattr(message, "_request_id", None), counted=counted["last"], input=message.usage.input_tokens,
                  cache_write=message.usage.cache_creation_input_tokens or 0, cache_read=message.usage.cache_read_input_tokens or 0,
                  output=message.usage.output_tokens, cost=cost, seconds=round(seconds, 2))

    out(f"{lesson_id:5} batch reply: {found[0]}{f' (+{len(found) - 1} more)' if len(found) > 1 else ''}: repairing in realtime")
    try:
        data, attempts = write_checked(client, cfg.model, system, ask, lesson, cfg.questions, retries=cfg.retries,
                                       max_tokens=cfg.max_tokens, out=lambda line: out(f"{lesson_id:5} {line.strip()}"),
                                       before=before, after=after, history=history)
        done = dict(status="passed", attempts=attempts, questions=data.model_dump()["questions"])
    except RepairFailed as error:
        done = dict(status="rejected", attempts=1 + len(spent), problems=error.found or [str(error)], last_reply=error.text)
    except (Refused, OverLimit) as error:
        done = dict(status="refused" if isinstance(error, Refused) else "over limit", attempts=1 + len(spent), problems=[str(error)])
    done["repair_cost"] = sum(spent)
    return done
