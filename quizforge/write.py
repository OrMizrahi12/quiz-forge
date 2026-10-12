"""Draft -> check -> revise (evaluator-optimizer). The writer agent drafts questions and saves them to bank/pending/; a checker
subagent, in a clean context, gives one verdict per question; the writer revises what isn't supported, until every question
is, or a stop fires. Writer and checker share one meter, so Limits.max_usd is the whole job's budget.
Nothing here writes to bank/approved/: only review.py does, after a person's yes."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from quizforge import agent, guards, memory, search, sources
from quizforge.library import load_lesson
from quizforge.prompts import for_schema, load_prompt
from quizforge.sanitize import clean
from quizforge.schema import Question, Questions
from quizforge.security.redact import redact_obj
from quizforge.validate import problems

SAVE = {
    "name": "save_questions",
    "description": "Saves the finished questions for one lesson to bank/pending/, where a checker and then a person "
    "review them. Code checks them first: the number of questions, four different options, a scenario "
    "that ends in a question, each quote word for word in the lesson, and each scenario new (not a "
    "repeat of one already in the bank). If a check fails, nothing is saved and the result lists the "
    "problems. Saving again replaces this job's earlier draft.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lesson_id": {"type": "string"},
            "questions": {"type": "array", "items": Question.model_json_schema()},
        },
        "required": ["lesson_id", "questions"],
    },
}


class Waiting(Exception):
    """The lesson already has questions waiting for review: a new job would overwrite them."""


@dataclass
class Job:
    lesson: str
    path: Path  # bank/pending/<lesson>.json, this job's draft
    questions: list = field(default_factory=list)  # the last saved draft
    verdicts: list = field(default_factory=list)  # the checker's verdicts on it
    saves: int = 0


@dataclass
class Result:
    stopped: str  # done, rounds limit, not saved, or the agent's stop: turn limit, budget, cut off, refused, ...
    who: str  # writer or checker: which run stopped the job
    rounds: int
    job: Job


def tools(cfg):
    return [search.tool(cfg.library)] + sources.tools(cfg.library) + [SAVE]


def save(cfg, job, lesson_id, questions):
    """The draft's checkpoint, in code: the rules, then item memory. A refusal says what to change; nothing is written."""
    if lesson_id != job.lesson:
        raise sources.NotChecked(
            f"this job writes questions for {job.lesson} only: save them with lesson_id {job.lesson}"
        )
    data = guards.draft(Questions.model_validate({"questions": questions}), seed=lesson_id)  # output layer
    lesson = clean(load_lesson(cfg.library, lesson_id))
    found = problems(data, lesson, cfg.questions) + guards.links(data)  # the rules, then the output layer's links
    known = memory.known_stems(cfg.bank, skip=job.path)  # every stem in the bank but this job's own draft
    found += memory.repeats([q.scenario for q in data.questions], known, cfg.similar)
    if found:
        raise sources.NotChecked("not saved: " + "; ".join(found) + ". Fix these and call save_questions again.")
    job.questions = [
        {**q.model_dump(), "section": search.section_of(cfg.library, lesson_id, q.quote)} for q in data.questions
    ]
    job.verdicts, job.saves = [], job.saves + 1
    keep(cfg, job)
    return f"saved {len(questions)} questions to bank/pending/{job.path.name}"


def keep(cfg, job, **extra):
    """bank/pending/<lesson>.json: the draft, its citations (the section of each quote) and the checker's verdicts."""
    job.path.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "lesson": job.lesson,
        "model": cfg.model,
        "prompt": cfg.prompt,
        "saved": datetime.now(UTC).isoformat(timespec="seconds"),
        "questions": job.questions,
        "verdicts": job.verdicts,
        **extra,
    }
    job.path.write_text(json.dumps(redact_obj(item), indent=2) + "\n")


def writer_act(cfg, job, out):
    """Our code runs every tool the writer asks for; a failure goes back as is_error, with what to fix."""

    def run(call):
        try:
            if call.name == "search_library":
                found = guards.tool_result(cfg, search.search_library(cfg.library, **call.input))  # input layer
                out(f"    search_library {call.input.get('query')!r}: {', '.join(r['source'] for r in found)}")
                return found, False
            if call.name == "check_quote":
                return sources.check_quote(cfg.library, **call.input), False
            if call.name == "save_questions":
                done = save(cfg, job, **call.input)
                out(f"    save_questions: {done}")
                return done, False
            return f"no tool named {call.name!r}", True
        except Exception as problem:
            if call.name == "save_questions":
                out(f"    save_questions: ERROR {str(problem)[:300]}")
            return str(problem), True

    return run


def checker_act(cfg):
    def run(call):
        result = sources.run(cfg.library, call)
        return result["content"], result["is_error"]

    return run


def brief(cfg, lesson_id):
    """The writer's first ask: the lesson's title and objectives, and the scenarios already in the bank for it."""
    row = next(
        r for r in json.loads((cfg.library / "MANIFEST.json").read_text())["lessons"] if r["lesson"] == lesson_id
    )
    goals = "\n".join(f"{n}. {goal}" for n, goal in enumerate(row["objectives"], 1))
    ask = (
        f'Write {cfg.questions} questions for lesson {lesson_id}, "{row["title"]}", and save them with save_questions.\n'
        f"The lesson's objectives:\n{goals}\n\nFind what you need with search_library (lesson_id {lesson_id}). Copy "
        "each quote word for word from a search result, and check it with check_quote before you save."
    )
    known = [stem for stem, where in memory.known_stems(cfg.bank) if where.endswith("/" + lesson_id)]
    if known:
        ask += (
            "\n\nThese scenarios are already in the bank for this lesson. Write different situations:\n- "
            + "\n- ".join(known)
        )
    return ask


def revision(cfg, job):
    """The writer's next ask, in a fresh context: the saved draft and the checker's verdicts, nothing else."""
    draft = [{k: v for k, v in q.items() if k != "section"} for q in job.questions]
    return (
        f"These questions for lesson {job.lesson} are saved in bank/pending/. A checker who saw only the questions "
        "and the lesson gave these verdicts:\n"
        + "\n".join(job.verdicts)
        + f"\n\nThe questions as saved:\n{json.dumps(draft, indent=1)}\n\nRevise every question that isn't supported: "
        "change the key, the options or the quote until the lesson supports the answer (search_library and "
        f"check_quote help). Keep the supported questions exactly as they are. Then save all {cfg.questions} "
        "questions again with save_questions."
    )


def check(meter, cfg, job, limits, out=print):
    """The checker subagent: a clean context that holds only the questions and the check_quote tool, never the writer's
    conversation. One verdict per question; a missing one counts as not supported."""
    outcome = agent.run(
        meter,
        cfg,
        sources.REVIEW,
        sources.tools(cfg.library),
        checker_act(cfg),
        sources.shown(job.lesson, job.questions),
        limits,
        out=out,
    )
    said = {line.split(":")[0]: line for line in sources.verdicts(outcome.text)}
    job.verdicts = [
        said.get(f"Question {n}", f"Question {n}: not supported: no verdict from the checker")
        for n in range(1, len(job.questions) + 1)
    ]
    return outcome


def write(meter, cfg, lesson_id, out=print):
    """One job: draft, check, revise, up to cfg.rounds drafts, within one turn limit per run and one budget for the job."""
    job = Job(lesson_id, cfg.bank / "pending" / f"{lesson_id}.json")
    if job.path.exists():
        raise Waiting(
            f"{lesson_id} already has questions waiting in bank/pending/: review them first "
            f"(python -m quizforge review --lesson {lesson_id})"
        )
    system = for_schema(load_prompt(cfg.prompts, cfg.prompt))
    limits = agent.Limits(max_turns=cfg.max_turns, max_usd=cfg.max_usd)
    for round_ in range(1, cfg.rounds + 1):
        out(f"{lesson_id} round {round_}: the writer {'drafts' if round_ == 1 else 'revises'}")
        meter.label, saves = f"{lesson_id} write round {round_} writer", job.saves
        ask = brief(cfg, lesson_id) if round_ == 1 else revision(cfg, job)
        wrote = agent.run(meter, cfg, system, tools(cfg), writer_act(cfg, job, out), ask, limits, out=out)
        if wrote.stopped != "done":
            return finish(cfg, job, Result(wrote.stopped, "writer", round_, job))
        if job.saves == saves:
            return finish(cfg, job, Result("not saved", "writer", round_, job))
        out(f"{lesson_id} round {round_}: the checker, in a clean context")
        meter.label = f"{lesson_id} write round {round_} checker"
        checked = check(meter, cfg, job, limits, out=out)
        for line in job.verdicts:
            out(f"  {line}")
        if checked.stopped != "done":
            return finish(cfg, job, Result(checked.stopped, "checker", round_, job))
        if all(sources.supported(line) for line in job.verdicts):
            return finish(cfg, job, Result("done", "checker", round_, job))
    return finish(cfg, job, Result("rounds limit", "checker", cfg.rounds, job))


def finish(cfg, job, result):
    """The draft stays in pending/ with how the job ended, for the person who reviews it."""
    if job.path.exists():
        keep(cfg, job, stopped=f"{result.stopped} ({result.who}, round {result.rounds})")
    return result
