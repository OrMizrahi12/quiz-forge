import time

import anthropic
from pydantic import ValidationError

from quizforge.schema import Questions
from quizforge.validate import problems

FORMAT = {"format": {"type": "json_schema", "schema": anthropic.transform_schema(Questions)}}


class Refused(Exception):
    """Claude declined. Don't send the same request again."""


class RepairFailed(Exception):
    """Still wrong after the last retry: stop, and say why."""

    def __init__(self, reason, found=(), text=""):
        super().__init__(reason)
        self.found, self.text = list(found), text


def write_checked(
    client,
    model,
    system,
    ask,
    lesson,
    count,
    retries=2,
    max_tokens=2000,
    out=print,
    before=lambda messages: None,
    after=lambda attempt, message, seconds: None,
    history=None,
):
    """Ask, check in code, and send the problems back until it passes, at most `retries` times.

    before(messages) runs before every request (the cost check); after(attempt, message, seconds) after
    every reply (the usage log), so a repair is counted and logged like the first attempt.
    history: a conversation that already holds attempt 1 and its problems (a batch reply): the loop goes on from there.
    """
    messages = list(history) if history else [{"role": "user", "content": ask}]
    found = []
    for attempt in range((len(messages) + 1) // 2, retries + 2):
        before(messages)
        start = time.perf_counter()
        message = client.messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages, output_config=FORMAT
        )
        after(attempt, message, time.perf_counter() - start)
        if message.stop_reason == "refusal":
            raise Refused(f"attempt {attempt}: Claude declined the request")
        if message.stop_reason == "max_tokens":
            raise RepairFailed(f"attempt {attempt}: cut off at max_tokens ({max_tokens})")
        text = message.content[0].text
        try:
            found = problems(Questions.model_validate_json(text), lesson, count)
        except ValidationError as error:
            found = [f"not valid against the schema: {error.errors()[0]['type']}"]
        shown = found[0] if found else "pass"
        if len(found) > 1:
            shown += f" (+{len(found) - 1} more)"
        out(f"  attempt {attempt}: {message.usage.input_tokens} input tokens, {shown}")
        if not found:
            return Questions.model_validate_json(text), attempt
        fix = "Fix these problems, and keep everything else:\n- " + "\n- ".join(found)
        messages += [{"role": "assistant", "content": text}, {"role": "user", "content": fix}]
    raise RepairFailed(f"still failing after {retries} retries: " + "; ".join(found), found, text)
