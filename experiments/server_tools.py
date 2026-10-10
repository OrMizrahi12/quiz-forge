import anthropic
from dotenv import load_dotenv

from quizforge.tools import cfg

load_dotenv()
client = anthropic.Anthropic()
FETCH = {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 3, "allowed_domains": ["platform.claude.com"]}
ASKS = [
    "Read https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use and "
    "tell me in one sentence where the results of parallel tool calls go.",
    "Read https://www.anthropic.com/news and tell me the latest headline.",
    "Fetch the tool runner page of the Claude docs on platform.claude.com and tell me what max_iterations does.",
]
for ask in ASKS:
    reply = client.messages.create(
        model=cfg.model, max_tokens=800, tools=[FETCH], messages=[{"role": "user", "content": ask}]
    )
    for block in reply.content:
        if block.type == "server_tool_use":
            print(f"server_tool_use {block.id[:18]} {block.input['url']}")
        elif block.type == "web_fetch_tool_result":
            error = getattr(block.content, "error_code", None)
            print(f"  web_fetch_tool_result: {error or 'the page, fetched by Anthropic'}")
    answer = next((block.text for block in reversed(reply.content) if block.type == "text"), "")
    print(f"  {reply.stop_reason}, {reply.usage.input_tokens} in: {answer[:70]!r}")
