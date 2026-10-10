"""The question writer's tools: read a lesson, check a quote, save questions (checked in code first)."""

import json

from quizforge import agent, sources
from quizforge.library import load_lesson
from quizforge.sanitize import clean
from quizforge.schema import Question, Questions
from quizforge.tools import TOOLS
from quizforge.validate import problems

SAVE = {
    "name": "save_questions",
    "description": "Saves the finished questions for one lesson to runs/agent/. Code checks them first: the number "
    "of questions, four different options, a scenario that ends in a question, and each quote word "
    "for word in the lesson. If a check fails, nothing is saved and the result lists the problems.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lesson_id": {"type": "string"},
            "questions": {"type": "array", "items": Question.model_json_schema()},
        },
        "required": ["lesson_id", "questions"],
    },
}


def tools(cfg):
    return [t for t in TOOLS if t["name"] == "read_lesson"] + sources.tools(cfg.library) + [SAVE]


def save_questions(cfg, lesson_id, questions, approve):
    """Irreversible, so two checkpoints before the write: the code checks, then a person."""
    data = Questions.model_validate({"questions": questions})
    found = problems(data, clean(load_lesson(cfg.library, lesson_id)), cfg.questions)
    if found:
        raise sources.NotChecked("not saved: " + "; ".join(found) + ". Fix these and call save_questions again.")
    if not approve(data):
        raise agent.Stop("declined")  # a person's no ends the task: it isn't Claude's to retry
    path = cfg.output_dir.parent / "agent" / f"{lesson_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.model_dump(), indent=2) + "\n")
    return f"saved {len(questions)} questions to {path.name}"


def act(cfg, approve):
    """Our code runs every tool Claude asks for; a failure goes back as is_error, with what to fix."""

    def run(call):
        try:
            if call.name == "save_questions":
                return save_questions(cfg, **call.input, approve=approve), False
            if call.name == "check_quote":
                return sources.check_quote(cfg.library, **call.input), False
            if call.name == "read_lesson":
                return clean(load_lesson(cfg.library, call.input["lesson_id"])), False
            return f"no tool named {call.name!r}", True
        except agent.Stop:
            raise
        except Exception as problem:
            return str(problem), True

    return run
