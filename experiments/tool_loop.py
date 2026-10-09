import html
import json
import re
import urllib.request
from urllib.parse import urlparse

import anthropic
from dotenv import load_dotenv

from quizforge.config import load_config
from quizforge.library import lesson_ids, load_lesson

load_dotenv()
client = anthropic.Anthropic()
cfg = load_config()
MANIFEST = json.loads((cfg.library / "MANIFEST.json").read_text())["lessons"]


def list_lessons():
    return "\n".join(f"{row['lesson']}: {row['title']}" for row in MANIFEST)


def read_lesson(lesson_id):
    return load_lesson(cfg.library, lesson_id)


def check_source(url):
    """An external system: our code makes the request, with a host allowlist and a timeout."""
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in ("support.claude.com", "platform.claude.com"):
        raise ValueError(f"not an allowed source: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "quiz-forge/0.2"})
    with urllib.request.urlopen(request, timeout=10) as page:
        title = re.search(r"<title[^>]*>(.*?)</title>", page.read(200_000).decode("utf-8", "replace"), re.S)
        return f"HTTP {page.status}; title: {html.unescape(title.group(1)).strip() if title else 'none'}"


TOOLS = [
    {"name": "list_lessons", "description": "Lists every lesson in the Quiz Forge library: its id and title, one per line.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_lesson", "description": "Returns the full notes of one lesson, as Markdown, by its id from list_lessons.",
     "input_schema": {"type": "object", "properties": {"lesson_id": {"type": "string", "enum": lesson_ids(cfg.library)}},
                      "required": ["lesson_id"]}},
    {"name": "check_source", "description": "Opens one https URL on support.claude.com or platform.claude.com and returns "
                                            "its HTTP status and page title, to confirm that a cited source is live.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
]
DISPATCH = {"list_lessons": list_lessons, "read_lesson": read_lesson, "check_source": check_source}


def run(call):
    """Harness dispatch: the name picks our function; an unknown name or a failure goes back as an error result."""
    try:
        content, error = DISPATCH[call.name](**call.input), False
    except Exception as problem:
        content, error = f"{type(problem).__name__}: {problem}", True
    print(f"    {call.name}({json.dumps(call.input)}) -> {'ERROR ' if error else ''}{content[:70]!r}")
    return {"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": error}


messages = [{"role": "user", "content": "Find the lesson about hallucinations and write one practice question about it. "
                                        "Then check that one support.claude.com source the lesson cites is live."}]
for turn in range(1, 9):   # a limit: a loop that never ends is a bill that never ends
    reply = client.messages.create(model=cfg.model, max_tokens=1500, tools=TOOLS, messages=messages)
    print(f"request {turn}: stop_reason {reply.stop_reason}, {reply.usage.input_tokens} in, {reply.usage.output_tokens} out")
    if reply.stop_reason != "tool_use":
        break
    messages += [{"role": "assistant", "content": reply.content},
                 {"role": "user", "content": [run(block) for block in reply.content if block.type == "tool_use"]}]
answer = next((block.text for block in reply.content if block.type == "text"), "")
open("runs/tool_loop.md", "w").write(answer + "\n")
print(f"answer: {len(answer)} characters -> runs/tool_loop.md")
