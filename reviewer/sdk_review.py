"""The Agent SDK reviewer: one query() per pending lesson file, on the model in config.toml, with the plugin's
write-exam-item Skill, read-only tools, a hook that keeps the reads in scope, and a structured verdict.
--ask resumes a saved review's session for one follow-up question."""

import argparse
import asyncio
import json
import sys
import tomllib
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, ResultMessage, SystemMessage, query
from dotenv import load_dotenv

from reviewer.verdict import Verdict

ROOT = Path(__file__).resolve().parent.parent
CONFIG = tomllib.loads((ROOT / "config.toml").read_text())
RUNS = ROOT / "runs" / "reviews"
SCOPE = ("bank/", "library/", "plugin/", ".claude/rules/")
SKILL = "quiz-forge-tools:write-exam-item"


async def stay_in_scope(input_data, tool_use_id, context):
    """PreToolUse: log every call; deny reads outside the bank, the library, the plugin and the rules."""
    args = input_data["tool_input"]
    target = args.get("file_path") or args.get("path") or args.get("pattern") or ""
    rel = target.removeprefix(str(ROOT)).removeprefix("/") or "."
    allowed = (rel + "/").startswith(SCOPE)  # "bank" and "bank/pending/x.json" are both in scope
    RUNS.mkdir(parents=True, exist_ok=True)
    with open(RUNS / "tools.log", "a") as log:
        log.write(f"{input_data['tool_name']} {rel} {'allowed' if allowed else 'denied'}\n")
    if allowed:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"{rel} is outside {', '.join(SCOPE)}",
        }
    }


def options(**changes):
    review = CONFIG["review"]
    settings = dict(
        model=CONFIG["model"]["reviewer"],
        cwd=str(ROOT),
        setting_sources=["project"],
        plugins=[{"type": "local", "path": str(ROOT / "plugin" / "quiz-forge-tools")}],
        skills=[SKILL],
        allowed_tools=["Read", "Glob", "Grep"],
        disallowed_tools=["Write", "Edit", "Bash", "Agent"],
        permission_mode="dontAsk",
        hooks={"PreToolUse": [HookMatcher(matcher="Read|Glob|Grep", hooks=[stay_in_scope])]},
        max_turns=review["max_turns"],
        max_budget_usd=review["max_usd"],
        env={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"},
    )
    return ClaudeAgentOptions(**{**settings, **changes})


async def review(path, **changes):
    """Review one pending file; save the verdict, its cost and the session id to runs/reviews/<lesson>.json."""
    item_id = Path(path).stem
    prompt = f"Review {path} with the {SKILL} checklist. Flag only problems that break a rule or the checklist."
    schema = {"type": "json_schema", "schema": Verdict.model_json_schema()}
    result = None
    async for message in query(prompt=prompt, options=options(output_format=schema, **changes)):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            print(f"{item_id}: {message.data['model']}, skill loaded: {SKILL in message.data.get('skills', [])}")
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.subtype != "success" or result.structured_output is None:
        raise SystemExit(f"{item_id}: no verdict ({result.subtype if result else 'no result'})")
    verdict = Verdict.model_validate(result.structured_output)
    saved = {
        "verdict": verdict.model_dump(),
        "total_cost_usd": result.total_cost_usd,
        "num_turns": result.num_turns,
        "session_id": result.session_id,
    }
    if not changes:  # a run with other options (--no-settings) is a trial: its verdict isn't saved
        RUNS.mkdir(parents=True, exist_ok=True)
        (RUNS / f"{item_id}.json").write_text(json.dumps(saved, indent=2) + "\n")
    print(
        f"{item_id}: {verdict.verdict} ${result.total_cost_usd:.4f} {result.num_turns} turns {'; '.join(verdict.reasons)}"
    )


async def ask(item_id, question):
    """One follow-up in the review's own session."""
    saved = json.loads((RUNS / f"{item_id}.json").read_text())
    if saved["verdict"]["item_id"] != item_id:  # one session per item: never continue another item's review
        raise SystemExit(f"{item_id}: the saved session belongs to {saved['verdict']['item_id']}")
    async for message in query(prompt=question, options=options(resume=saved["session_id"])):
        if isinstance(message, ResultMessage):
            print(message.result)


def main(argv=None):
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(prog="python -m reviewer.sdk_review")
    parser.add_argument("files", nargs="*", help="pending lesson files, e.g. bank/pending/L1.3.json")
    parser.add_argument(
        "--ask", nargs=2, metavar=("LESSON", "QUESTION"), help="a follow-up in a saved review's session"
    )
    parser.add_argument(
        "--no-settings", action="store_true", help="no project settings and no plugin: the skill is gone"
    )
    args = parser.parse_args(argv)
    changes = {"setting_sources": [], "plugins": []} if args.no_settings else {}
    if args.ask:
        asyncio.run(ask(*args.ask))
    for path in args.files:
        asyncio.run(review(path, **changes))


if __name__ == "__main__":
    sys.exit(main())
