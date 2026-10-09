"""Many lessons as one Message Batch: half the price, results within 24 hours."""
import json

from pydantic import ValidationError

from quizforge.config import ROOT
from quizforge.generate import user_turn
from quizforge.library import load_lesson
from quizforge.prompts import for_schema, load_prompt
from quizforge.repair import FORMAT
from quizforge.sanitize import clean
from quizforge.schema import Questions
from quizforge.validate import problems

SENT = ROOT / "runs" / "batches.jsonl"   # one line per batch we submitted


def custom_id(lesson_id, version):
    """Letters, digits, - and _ only, up to 64: L3.2 with v4 -> L3_2-v4."""
    return f"{lesson_id.replace('.', '_')}-{version}"


def lesson_of(cid):
    return cid.split("-")[0].replace("_", ".")


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


def collect(client, cfg, batch_id):
    """Each result, matched to its lesson by custom_id, then checked in code."""
    for result in client.messages.batches.results(batch_id):
        cid, outcome = result.custom_id, result.result
        if outcome.type != "succeeded":
            why = outcome.error.error.type if outcome.type == "errored" else ""
            yield cid, f"{outcome.type} {why}".strip(), None
            continue
        reply = outcome.message
        lesson = clean(load_lesson(cfg.library, lesson_of(cid)))
        try:
            data = Questions.model_validate_json(reply.content[0].text)
            found = problems(data, lesson, cfg.questions)
        except ValidationError:
            found = ["not valid against the schema"]
        yield cid, found[0] if found else "passed", reply.usage
