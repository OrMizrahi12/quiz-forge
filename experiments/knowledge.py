"""Three ways to get the library into context for one question: paste it all, retrieve three sections, or let Claude search."""

from quizforge import retrieve, usage
from quizforge.client import make_client
from quizforge.config import load_config
from quizforge.library import lesson_ids, load_lesson
from quizforge.meter import Meter

cfg = load_config()
prices = usage.load_prices("pricing.toml")
QUESTIONS = [
    ("What should you check first when an answer might contain a hallucination?", "L3.2"),
    ("When is a chain of prompts better than one prompt?", "L2.2"),
    ("What does latency mean when you choose a model tier?", "L1.3"),
]
SEARCH = {
    "name": "search_library",
    "description": "Searches the course library and returns the three lesson sections that best match the query, "
    "as search results you can cite. Use short queries with the key words; search again with "
    "different words if the results don't answer the question.",
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
}
ASK = "Answer in two or three sentences, from the course library only, and cite it."


def cited(reply):
    """The sources Claude cited, from the citations on its text blocks."""
    return sorted(
        {c.source for b in reply.content if b.type == "text" for c in (b.citations or []) if hasattr(c, "source")}
    )


def paste_all(meter, question):
    everything = "\n\n".join(load_lesson(cfg.library, l) for l in lesson_ids(cfg.library))
    reply = meter.messages.create(
        model=cfg.model,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"<library>\n{everything}\n</library>"},
                    {"type": "text", "text": f"{question} {ASK}"},
                ],
            }
        ],
    )
    said = "".join(b.text for b in reply.content if b.type == "text")
    named = sorted(
        {l for l in lesson_ids(cfg.library) if l in said or f"Lesson {l[1:]}" in said}
    )  # no citations: only what it names
    return reply, named


def retrieved(meter, question):
    found = retrieve.search(cfg.library, question)
    reply = meter.messages.create(
        model=cfg.model,
        max_tokens=400,
        messages=[
            {"role": "user", "content": [*retrieve.as_results(found), {"type": "text", "text": f"{question} {ASK}"}]}
        ],
    )
    return reply, cited(reply)


def agentic(meter, question, turns=4):
    messages = [{"role": "user", "content": f"{question} {ASK} Use search_library."}]
    for _ in range(turns):
        reply = meter.messages.create(model=cfg.model, max_tokens=400, tools=[SEARCH], messages=messages)
        if reply.stop_reason != "tool_use":
            break
        results = [
            {
                "type": "tool_result",
                "tool_use_id": b.id,
                "content": retrieve.as_results(retrieve.search(cfg.library, b.input["query"])),
            }
            for b in reply.content
            if b.type == "tool_use"
        ]
        messages += [{"role": "assistant", "content": reply.content}, {"role": "user", "content": results}]
    return reply, cited(reply)


for way in (paste_all, retrieved, agentic):
    meter, right = Meter(make_client(), prices, cfg.model), 0
    for question, lesson in QUESTIONS:
        reply, sources = way(meter, question)
        hit = any(s.startswith(lesson) for s in sources)
        right += hit
        print(
            f"{way.__name__:10} {lesson}: {'cited' if way is not paste_all else 'named'} {', '.join(sources) or 'nothing'}"
        )
    print(
        f"{way.__name__:10} {meter.requests} requests, {meter.tokens_in:7,} input tokens, ${meter.cost:.4f}, "
        f"right lesson {right} of {len(QUESTIONS)}\n"
    )
