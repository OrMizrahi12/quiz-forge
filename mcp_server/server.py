"""The course-library MCP server. Resources: the lessons. Tools: search, objectives, quote checks.
Prompt: write-items. A host runs it over stdio (python -m mcp_server.server), so never print:
stdout is the wire."""
import json
import sys
from typing import Annotated, TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver import Elicit, Resolve
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from quizforge.config import load_config
from quizforge.library import lesson_ids, load_lesson
from quizforge.search import search_library
from quizforge.sources import NotChecked, check_quote as find_quote

LIBRARY = load_config().library  # an absolute path: the host may start us from any folder
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
LessonId = Annotated[str, Field(description="A lesson id, e.g. L1.3")]

mcp = MCPServer(
    "quiz-library",
    instructions="Read-only access to the Quiz Forge lesson library: search it, read a lesson, "
    "get its objectives, and check that a quote is word for word.",
)


class Section(TypedDict):
    source: str
    text: str


@mcp.resource("lesson://{lesson_id}", mime_type="text/markdown")
def lesson(lesson_id: str) -> str:
    """One lesson's notes, in full."""
    if lesson_id not in lesson_ids(LIBRARY):
        known = ", ".join(lesson_ids(LIBRARY))
        raise ResourceNotFoundError(f"no lesson {lesson_id!r}; the library has {known}")
    return load_lesson(LIBRARY, lesson_id)


@mcp.tool(title="Search the lessons", annotations=READ_ONLY)
def search_lessons(
    query: Annotated[str, Field(description="A few key words, e.g. model tier latency")],
    lesson_id: Annotated[str | None, Field(description="Optional: search one lesson only")] = None,
) -> list[Section]:
    """The three lesson sections that best match a few key words."""
    try:
        found = search_library(LIBRARY, query, lesson_id)
    except ValueError as e:
        raise ToolError(str(e))
    return [Section(source=r["source"], text=r["content"][0]["text"]) for r in found]


@mcp.tool(title="Get a lesson's objectives", annotations=READ_ONLY)
def get_objectives(lesson_id: LessonId) -> list[str]:
    """The learning objectives of one lesson, from the library's manifest."""
    manifest = json.loads((LIBRARY / "MANIFEST.json").read_text())
    for row in manifest["lessons"]:
        if row["lesson"] == lesson_id:
            return row["objectives"]
    raise ToolError(f"unknown lesson id {lesson_id!r}: ids look like L1.3")


class Lesson(BaseModel):
    lesson_id: str = Field(description="The lesson the quote comes from, e.g. L1.3")


async def ask_lesson(lesson_id: str = "") -> Lesson | Elicit[Lesson]:
    """No lesson given? Ask the person (elicitation), not the model."""
    if lesson_id:
        return Lesson(lesson_id=lesson_id)
    return Elicit("Which lesson is the quote from?", Lesson)


@mcp.tool(title="Check a quote", annotations=READ_ONLY)
def check_quote(
    quote: Annotated[str, Field(description="The full sentence the item quotes")],
    lesson: Annotated[Lesson, Resolve(ask_lesson)],
    lesson_id: Annotated[str, Field(description="e.g. L1.3; empty: ask the person")] = "",
) -> str:
    """Whether a quote appears word for word in a lesson; if not, the lesson's closest sentence."""
    try:
        return find_quote(LIBRARY, lesson.lesson_id, quote)
    except NotChecked as e:
        raise ToolError(str(e))


@mcp.prompt(name="write-items", title="Write practice items")
def write_items(lesson_id: str, count: str = "2") -> str:
    """Draft practice items for one lesson, for a person to review."""
    return (
        f"Read lesson://{lesson_id} and its objectives. Write {count} practice items to the "
        "item standard, each quoting one exact sentence that check_quote confirms. Save them "
        "to bank/pending/ and stop: a person reviews them with qf review."
    )


if __name__ == "__main__":
    if "--http" in sys.argv:  # reached by URL: Streamable HTTP, on this machine only
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8765)
    else:  # a host starts us and talks over stdin and stdout
        mcp.run()
