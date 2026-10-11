"""The LLM judge: one item and its lesson section in, a schema-checked verdict out. Model and rubric version in
config.toml [judge]; the rubric is a locked prompt in prompts/judge/."""
import tomllib
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from quizforge import retrieve
from quizforge.config import ROOT
from quizforge.prompts import load_prompt
from quizforge.sanitize import clean
from quizforge.validate import words

SETTINGS = tomllib.loads((ROOT / "config.toml").read_text())["judge"]


class Verdict(BaseModel):
    reason: str = Field(description="One sentence: the deciding problem, or why the item holds")
    failed_criterion: Literal["none", "constraint", "one_key", "distractors", "supported", "giveaway", "parallel"]
    verdict: Literal["good", "bad"]


FORMAT = {"format": {"type": "json_schema", "schema": anthropic.transform_schema(Verdict)}}


def section(library, lesson_id, quote):
    """The lesson section the quote comes from: the judge sees the evidence, not the whole lesson."""
    for chunk in retrieve.chunks(library):
        if chunk["source"].startswith(lesson_id + "#") and words(quote) in words(chunk["text"]):
            return clean(chunk["text"])
    return "(the quote is not in this lesson)"


def judge(meter, library, item, version=None):
    q = item["item"]
    options = "\n".join(f"{key.upper()}) {q[key]}" for key in "abcd")
    shown = (f"<item>\n{q['scenario']}\n{options}\nKey: {q['answer']}\nQuote: {q['quote']}\n</item>\n\n"
             f"<lesson_section>\n{section(library, item['lesson'], q['quote'])}\n</lesson_section>")
    reply = meter.messages.create(
        model=meter.model, max_tokens=4000, output_config=FORMAT,  # room for thinking: it counts toward max_tokens
        system=load_prompt(ROOT / "prompts/judge", version or SETTINGS["prompt"]),
        messages=[{"role": "user", "content": shown}],
    )
    return Verdict.model_validate_json(next(block.text for block in reply.content if block.type == "text"))
