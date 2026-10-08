import anthropic
from pydantic import ValidationError

from quizforge.schema import Questions
from quizforge.validate import problems

FORMAT = {"format": {"type": "json_schema", "schema": anthropic.transform_schema(Questions)}}


class Refused(Exception):
    """Claude declined. Don't send the same request again."""


class RepairFailed(Exception):
    """Still wrong after the last retry: stop, and say why."""


def write_checked(client, model, system, ask, lesson, count,
                  retries=2, max_tokens=2000, out=print):
    messages = [{"role": "user", "content": ask}]
    for attempt in range(1, retries + 2):
        message = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                         messages=messages, output_config=FORMAT)
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
    raise RepairFailed(f"still failing after {retries} retries: " + "; ".join(found))
