import time

import anthropic
from anthropic import beta_tool
from anthropic.lib.tools import ToolError
from dotenv import load_dotenv

from quizforge import tools
from quizforge.tools import cfg

load_dotenv()
client = anthropic.Anthropic()


@beta_tool
def list_lessons() -> str:
    """Lists every lesson in the Quiz Forge library: its id and title, one per line."""
    return tools.list_lessons()


@beta_tool
def read_lesson(lesson_id: str) -> str:
    """Returns the full notes of one lesson, as Markdown.

    Args:
        lesson_id: The lesson's id from list_lessons, such as L3.2.
    """
    return tools.read_lesson(lesson_id)


@beta_tool
def check_source(url: str) -> str:
    """Opens one https URL and returns its HTTP status and page title: is a source live?

    Args:
        url: A full https URL on support.claude.com or platform.claude.com.
    """
    try:
        return tools.check_source(url)
    except Exception as problem:  # a ToolError goes back with is_error, without a traceback
        raise ToolError(f"{type(problem).__name__}: {problem}")


print("read_lesson, as the decorator wrote it:", read_lesson.to_dict()["input_schema"])
ASK = "Check every source that lesson L3.2 cites, and give me a short report."
runner = client.beta.messages.tool_runner(
    model=cfg.model,
    max_tokens=1500,
    max_iterations=8,
    tools=[list_lessons, read_lesson, check_source],
    messages=[{"role": "user", "content": ASK}],
)
for turn, reply in enumerate(runner, 1):
    calls = [block for block in reply.content if block.type == "tool_use"]
    print(f"request {turn}: {reply.stop_reason}, {len(calls)} tool calls")
    started = time.perf_counter()
    results = runner.generate_tool_call_response()  # the runner runs them here, and reuses them
    if results:
        print(f"  {len(results['content'])} results, {time.perf_counter() - started:.1f} s")
report = next((block.text for block in reply.content if block.type == "text"), "")
open("runs/runner.md", "w").write(report + "\n")
print("report -> runs/runner.md")
