"""The source-checking tool: does a question's quote really come from its lesson? Claude asks, our code checks."""

import re
from concurrent.futures import ThreadPoolExecutor

from quizforge.library import lesson_ids, load_lesson
from quizforge.sanitize import clean
from quizforge.validate import words


class NotChecked(Exception):
    """The check couldn't run: the message says what to send instead."""


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.split()) >= 4]


def check_quote(library, lesson_id, quote):
    """'found', or 'not found' with the lesson's closest sentence, so Claude can correct the quote."""
    if lesson_id not in lesson_ids(library):
        raise NotChecked(f"unknown lesson id {lesson_id!r}: ids look like L1.3; use the lesson id the question cites")
    if len(quote.split()) < 4:
        raise NotChecked("the quote is too short to check: send the full sentence the question quotes")
    lesson = clean(load_lesson(library, lesson_id))
    if words(quote) in words(lesson):
        return f"found in {lesson_id}"
    wanted = set(words(quote).split())
    nearest = max(sentences(lesson), key=lambda s: len(wanted & set(words(s).split())))
    return f"not found in {lesson_id}. Closest sentence: {nearest[:300]!r}"


def tools(library):
    """One tool, described for Claude: what it does, when to use it, what each input is, what it can't do."""
    return [
        {
            "name": "check_quote",
            "description": "Checks whether a quote appears word for word in one lesson of the Quiz Forge library "
            "(case and punctuation are ignored). Returns 'found', or 'not found' with the lesson's "
            "closest sentence. Use it once for every question's quote before you judge the question; "
            "check several quotes at once when you can. It reads only the library: it can't check "
            "web pages or anything outside the lesson.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lesson_id": {
                        "type": "string",
                        "enum": lesson_ids(library),
                        "description": "The lesson the quote should come from, e.g. L1.3",
                    },
                    "quote": {"type": "string", "description": "The quote, exactly as the question gives it"},
                },
                "required": ["lesson_id", "quote"],
            },
        }
    ]


def run(library, call):
    """Harness dispatch: our function runs; a failure goes back as an is_error result that says what to do."""
    try:
        if call.name != "check_quote":
            raise NotChecked(f"no tool named {call.name!r}: the only tool is check_quote")
        content, error = check_quote(library, **call.input), False
    except (NotChecked, TypeError) as problem:
        content, error = str(problem), True
    return {"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": error}


def run_all(library, calls):
    """Every tool_use block of one reply, run at once; the results keep their order, for one user message."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda call: run(library, call), calls))


REVIEW = (
    "You review practice questions written from one lesson. For each question, check its quote with "
    "check_quote, then decide whether the quote supports the answer marked correct. Reply with one line "
    "per question, exactly: 'Question <n>: supported' or 'Question <n>: not supported: <reason>'."
)


def shown(lesson_id, questions):
    """What the reviewer sees: each question, the key, and its quote. Not the writer's reasons, not its conversation."""
    return "\n\n".join(
        f"Question {n}: {q['scenario']}\nA) {q['a']}\nB) {q['b']}\nC) {q['c']}\nD) {q['d']}\n"
        f'Correct: {q["answer"]}\nQuote from {lesson_id}: "{q["quote"]}"'
        for n, q in enumerate(questions, 1)
    )


def verdicts(text):
    """The verdict lines of a reply: 'Question <n>: supported' or 'Question <n>: not supported: <reason>'."""
    return [line.strip() for line in text.splitlines() if line.strip().startswith("Question ")]


def supported(line):
    """True when the word right after the first colon is 'supported': 'Question 1: supported' and also
    'Question 1: supported, the quote matches'. 'Question 1: not supported: ...' starts with another word."""
    after = line.partition(":")[2].strip().lower()
    return re.match(r"supported\b", after) is not None


def review(client, cfg, lesson_id, questions, max_turns=4, out=print):
    """A manual tool loop: Claude checks every quote through our tool, then judges each question.

    Returns (verdicts, calls, usages): one 'supported'/'not supported' line per question, the number of
    check_quote calls, and each reply's usage.
    """
    messages, calls, usages = [{"role": "user", "content": shown(lesson_id, questions)}], 0, []
    for turn in range(1, max_turns + 1):
        reply = client.messages.create(
            model=cfg.model, max_tokens=800, system=REVIEW, tools=tools(cfg.library), messages=messages
        )
        usages.append(reply.usage)
        uses = [block for block in reply.content if block.type == "tool_use"]
        out(f"  turn {turn}: {reply.stop_reason}, {len(uses)} check_quote call(s)")
        if reply.stop_reason != "tool_use":
            return verdicts("".join(block.text for block in reply.content if block.type == "text")), calls, usages
        calls += len(uses)
        results = run_all(cfg.library, uses)
        for result in results:
            out(f"    check_quote: {'ERROR ' if result['is_error'] else ''}{result['content'][:60]!r}")
        messages += [{"role": "assistant", "content": reply.content}, {"role": "user", "content": results}]
    raise RuntimeError(f"no verdict after {max_turns} turns")
