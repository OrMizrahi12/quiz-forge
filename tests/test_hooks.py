import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "plugin" / "quiz-forge-tools" / "scripts"


def hook(name, event):
    return subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": ""},
    )


def test_guard_blocks_a_write_to_approved():
    run = hook("guard_approved.py", {"tool_name": "Write", "tool_input": {"file_path": "bank/approved/x.json"}})
    assert run.returncode == 2
    assert "python -m quizforge review" in run.stderr


def test_guard_lets_pending_through():
    run = hook("guard_approved.py", {"tool_name": "Write", "tool_input": {"file_path": "bank/pending/x.json"}})
    assert run.returncode == 0


def test_guard_blocks_a_bash_move_into_approved():
    run = hook(
        "guard_approved.py", {"tool_name": "Bash", "tool_input": {"command": "mv bank/pending/a.json bank/approved/"}}
    )
    assert run.returncode == 2


def test_guard_blocks_claude_running_the_review():
    run = hook(
        "guard_approved.py",
        {"tool_name": "Bash", "tool_input": {"command": "echo y | .venv/bin/python -m quizforge review"}},
    )
    assert run.returncode == 2


def test_stop_hook_lets_a_second_stop_through():
    run = hook("tests_on_stop.py", {"stop_hook_active": True})
    assert run.returncode == 0
