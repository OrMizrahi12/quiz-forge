"""End to end: the command line as a person runs it, in a fresh copy of the app, against the local mock: no key, no
cost. It checks the wiring (command, config, prompt, checks, files, logs); the model's quality is the eval's job."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.mock_api import serve

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.e2e
def test_generate_from_the_command_line(tmp_path):
    for folder in ("quizforge", "prompts", "library"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    for name in ("config.toml", "pricing.toml"):
        shutil.copy(ROOT / name, tmp_path)
    mock = serve(["tokens", f"reply:{ROOT / 'tests/fixtures/reply_L0.1.json'}"])
    env = {**os.environ, "ANTHROPIC_BASE_URL": "http://127.0.0.1:8787", "ANTHROPIC_API_KEY": "mock-not-a-real-key"}
    try:
        run = subprocess.run([sys.executable, "-m", "quizforge", "generate", "--lesson", "L0.1"], cwd=tmp_path,
                             env=env, capture_output=True, text=True, timeout=120)
    finally:
        mock.shutdown()
        mock.server_close()
    assert run.returncode == 0, run.stdout + run.stderr
    saved = json.loads((tmp_path / "runs/items/L0.1.json").read_text())
    assert saved["status"] == "passed" and len(saved["questions"]) == 2
    assert json.loads((tmp_path / "runs/usage.jsonl").read_text())["request_id"] == "req_mock_2"
