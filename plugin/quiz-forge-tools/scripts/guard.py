"""PreToolUse (Bash|Write|Edit|Read): Quiz Forge's destructive-action policy (quizforge/security/guard.py) as the hook's
decision. deny and ask go back as JSON with a reason; allow prints nothing, so the normal permission rules decide."""

import json
import os
import sys
from pathlib import Path

event = json.load(sys.stdin)
root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()
sys.path.insert(0, str(root))
from quizforge.security.guard import decide  # the project's own policy, imported from the project

decision = decide(event.get("tool_name"), event.get("tool_input", {}), root)
if decision.kind != "allow":
    output = {"hookEventName": "PreToolUse", "permissionDecision": decision.kind}
    print(json.dumps({"hookSpecificOutput": output | {"permissionDecisionReason": decision.reason}}))
