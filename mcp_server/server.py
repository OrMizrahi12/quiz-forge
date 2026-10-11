"""The course-library MCP server. Resources: the lessons. Tools: search, objectives, quote checks.
Prompt: write-items. One build, two transports: a host runs it over stdio (python -m mcp_server.server), a remote
client reaches it over Streamable HTTP (--http) with a bearer token. Never print: on stdio, stdout is the wire."""

import json
import sys
from pathlib import Path
from typing import Annotated, TypedDict

from mcp.server import MCPServer
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Elicit, Resolve
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import ToolAnnotations
from pydantic import AnyHttpUrl, BaseModel, Field

from mcp_server.auth import HASHES, RESOURCE, HashedTokenVerifier
from quizforge.config import load_config
from quizforge.library import lesson_ids, load_lesson
from quizforge.search import search_library
from quizforge.sources import NotChecked, check_quote as find_quote

LIBRARY = load_config().library  # an absolute path: the host may start us from any folder
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
LessonId = Annotated[str, Field(description="A lesson id, e.g. L1.3")]
INSTRUCTIONS = (
    "Read-only access to the Quiz Forge lesson library: search it, read a lesson, "
    "get its objectives, and check that a quote is word for word."
)
# What Claude reads to pick a tool: what it returns, when to use it, and what it can't do.
SEARCH = (
    "The three lesson sections that best match a few key words, each with its source (lesson id and heading). "
    "Use it to find which lesson covers a topic. It can't match meaning, only words, and it searches only this library."
)
OBJECTIVES = (
    "The learning objectives of one lesson, from the library's manifest. Use it once you know the lesson id. "
    "It can't search: find the lesson with search_lessons first."
)
QUOTE = (
    "Whether a quote appears word for word in one lesson (case and punctuation ignored); if not, the lesson's "
    "closest sentence. Send the full sentence: it can't check a few words or anything outside the library."
)


class Section(TypedDict):
    source: str
    text: str


class Lesson(BaseModel):
    lesson_id: str = Field(description="The lesson the quote comes from, e.g. L1.3")


def known():
    return ", ".join(lesson_ids(LIBRARY))


async def ask_lesson(lesson_id: str = "") -> Lesson | Elicit[Lesson]:
    """No lesson given? Ask the person (elicitation), not the model."""
    if lesson_id:
        return Lesson(lesson_id=lesson_id)
    return Elicit("Which lesson is the quote from?", Lesson)


def build(http: bool = False, hashes: Path = HASHES) -> MCPServer:
    """The same resources, tools and prompt for both transports. Over HTTP every request needs a token that the
    verifier knows; over stdio the boundary is the process that started us, so there is nothing to check."""
    auth = {}
    if http:
        auth = {
            "token_verifier": HashedTokenVerifier(hashes),
            "auth": AuthSettings(
                issuer_url=AnyHttpUrl("https://idp.example.com"),  # a placeholder: no identity provider here
                resource_server_url=AnyHttpUrl(RESOURCE),
                required_scopes=["library:read"],
                validate_token_resource=True,
            ),
        }
    mcp = MCPServer("quiz-library", instructions=INSTRUCTIONS, **auth)

    @mcp.resource("lesson://{lesson_id}", mime_type="text/markdown")
    def lesson(lesson_id: str) -> str:
        """One lesson's notes, in full."""
        if lesson_id not in lesson_ids(LIBRARY):
            raise ResourceNotFoundError(f"no lesson {lesson_id!r}; the library has {known()}")
        return load_lesson(LIBRARY, lesson_id)

    @mcp.tool(title="Search the lessons", description=SEARCH, annotations=READ_ONLY)
    def search_lessons(
        query: Annotated[str, Field(description="A few key words, e.g. model tier latency")],
        lesson_id: Annotated[str | None, Field(description="Optional: search one lesson only")] = None,
    ) -> list[Section]:
        try:
            found = search_library(LIBRARY, query, lesson_id)
        except ValueError as e:
            raise ToolError(str(e))
        return [Section(source=r["source"], text=r["content"][0]["text"]) for r in found]

    @mcp.tool(title="Get a lesson's objectives", description=OBJECTIVES, annotations=READ_ONLY)
    def get_objectives(lesson_id: LessonId) -> list[str]:
        manifest = json.loads((LIBRARY / "MANIFEST.json").read_text())
        for row in manifest["lessons"]:
            if row["lesson"] == lesson_id:
                return row["objectives"]
        raise ToolError(f"unknown lesson id {lesson_id!r}: the library has {known()}")

    @mcp.tool(title="Check a quote", description=QUOTE, annotations=READ_ONLY)
    def check_quote(
        quote: Annotated[str, Field(description="The full sentence the item quotes")],
        lesson: Annotated[Lesson, Resolve(ask_lesson)],
        lesson_id: Annotated[str, Field(description="e.g. L1.3; empty: ask the person")] = "",
    ) -> str:
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

    return mcp


mcp = build()  # the stdio build: what tests and in-process clients use

if __name__ == "__main__":
    if "--http" in sys.argv:  # reached by URL: Streamable HTTP, on this machine only, with a token
        build(http=True).run(transport="streamable-http", host="127.0.0.1", port=8765)
    else:  # a host starts us and talks over stdin and stdout
        mcp.run()
