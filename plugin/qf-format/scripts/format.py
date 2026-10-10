"""PostToolUse (Edit|Write): ruff formats a Python file right after Claude edits it."""

import json
import os
import subprocess
import sys
from pathlib import Path

event = json.load(sys.stdin)
path = event.get("tool_input", {}).get("file_path", "")
venv_ruff = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".venv" / "bin" / "ruff"
if path.endswith(".py"):
    subprocess.run([str(venv_ruff) if venv_ruff.exists() else "ruff", "format", "--quiet", path])
sys.exit(0)
