"""PreToolUse (Edit|Write|Bash): only a person running python -m quizforge review writes to bank/approved/."""

import json
import os
import sys
from pathlib import Path

event = json.load(sys.stdin)
tool, args = event.get("tool_name"), event.get("tool_input", {})
root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()
approved = root / "bank" / "approved"

if tool in ("Edit", "Write"):
    target = (root / args.get("file_path", "")).resolve()
    blocked = target == approved or approved in target.parents
else:
    command = args.get("command", "")
    blocked = "bank/approved" in command or "quizforge review" in command

if blocked:
    print("bank/approved/ is written only by a person running python -m quizforge review", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
