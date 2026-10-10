"""Stop: Claude can't finish a turn that changed Python files while the tests fail."""

import json
import os
import subprocess
import sys
from pathlib import Path

event = json.load(sys.stdin)
root = os.environ.get("CLAUDE_PROJECT_DIR", ".")
if event.get("stop_hook_active"):
    sys.exit(0)
changed = subprocess.run(
    ["git", "status", "--porcelain", "--", "*.py"], capture_output=True, text=True, cwd=root
).stdout
if not changed.strip():  # no Python file changed: nothing to test
    sys.exit(0)
venv_python = Path(root) / ".venv" / "bin" / "python"
python = str(venv_python) if venv_python.exists() else sys.executable
tests = subprocess.run([python, "-m", "pytest", "-q", "-x"], capture_output=True, text=True, cwd=root)
if tests.returncode != 0:
    tail = "\n".join(tests.stdout.splitlines()[-20:])
    print(f"The tests fail. Fix them before you stop:\n{tail}", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
