"""The same policy in the Agent SDK: one query() on the writer's model (Claude Haiku 4.5) that may use Bash and nothing
else, in dontAsk mode, with quizforge/security/guard.py as its PreToolUse hook. Asked for a recursive rm outside
runs/scratch/, the call is denied before it runs and the reason goes back to Claude as the tool result.
Usage: python -m experiments.sdk_guard_demo"""

import asyncio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)
from dotenv import load_dotenv

from quizforge.config import ROOT, load_config
from quizforge.security.guard import decide

ASK = "Run exactly this command, then tell me in one sentence what happened: rm -rf runs/old-exports"


async def guard(input_data, tool_use_id, context):
    decision = decide(input_data["tool_name"], input_data["tool_input"], ROOT)
    if decision.kind == "allow":
        return {}
    output = {"hookEventName": "PreToolUse", "permissionDecision": decision.kind}
    return {"hookSpecificOutput": output | {"permissionDecisionReason": decision.reason}}


async def main():
    load_dotenv(ROOT / ".env")
    options = ClaudeAgentOptions(
        model=load_config().model,
        cwd=str(ROOT),
        tools=["Bash"],
        allowed_tools=["Bash"],
        permission_mode="dontAsk",
        setting_sources=[],  # no project settings and no plugins: only this hook stands in the way
        hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[guard])]},
        max_turns=4,
    )
    async for message in query(prompt=ASK, options=options):
        for block in getattr(message, "content", []) if isinstance(message, (AssistantMessage, UserMessage)) else []:
            if isinstance(block, ToolUseBlock):
                print(f"Claude calls {block.name}: {block.input.get('command')}")
            elif isinstance(block, ToolResultBlock):
                print(f"tool result{' (error)' if block.is_error else ''}: {block.content}")
            elif isinstance(block, TextBlock):
                print(f"Claude: {block.text}")
        if isinstance(message, ResultMessage):
            print(f"cost ${message.total_cost_usd:.4f}")
    print("runs/old-exports is still there:", (ROOT / "runs/old-exports").exists())


asyncio.run(main())
