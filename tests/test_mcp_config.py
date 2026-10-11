"""Lab 6: the server shared with the team at project scope, with least privilege, and no token in any config."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READ_TOOLS = {
    "mcp__quiz-library__search_lessons",
    "mcp__quiz-library__get_objectives",
    "mcp__quiz-library__check_quote",
}


def test_mcp_json_shares_the_library_server():
    entry = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["quiz-library"]
    assert entry["command"] == ".venv/bin/python" and entry["args"] == ["-m", "mcp_server.server"]


def test_no_token_in_shared_config():
    for name in (".mcp.json", ".claude/settings.json"):
        text = (ROOT / name).read_text().lower()
        assert "bearer" not in text and "authorization" not in text, name


def test_only_the_read_tools_are_allowed():
    allow = json.loads((ROOT / ".claude/settings.json").read_text())["permissions"]["allow"]
    assert {rule for rule in allow if rule.startswith("mcp__")} == READ_TOOLS
    assert not [rule for rule in allow if rule.startswith("mcp__") and "*" in rule]
