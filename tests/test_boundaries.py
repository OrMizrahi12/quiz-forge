"""9.6: what a deployment can reach. Its settings, library and bank come from QF_HOME; the library server it starts
is told which deployment it serves; a lesson outside its library is refused; the fleet view holds no content."""

import json
import os
import subprocess
import sys

import pytest

from quizforge import fleet, library_client
from quizforge.config import CODE, ROOT
from quizforge.init import init
from quizforge.library import load_lesson

SAMPLE = CODE / "examples/sample-library/v1"


@pytest.fixture
def bakery(tmp_path):
    folder = tmp_path / "bakery"
    init(folder, SAMPLE, "bakery", "home bakers learning to make bread")
    return folder


def settings_in(folder):
    """load_config() in a fresh process with QF_HOME set, as qf runs."""
    code = "from quizforge.config import load_config; c = load_config(); print(c.library, c.bank, c.usage_log)"
    env = {**os.environ, "QF_HOME": str(folder)}
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True).stdout


def test_a_deployment_reads_its_own_settings_library_bank_and_log(bakery):
    assert settings_in(bakery).split() == [str(bakery / p) for p in ("library", "bank", "runs/usage.jsonl")]


def test_a_lesson_outside_the_library_is_refused(bakery):
    with pytest.raises(ValueError, match="unknown lesson"):
        load_lesson(bakery / "library", "../../ccao-f/v1/L1.1")


def test_the_library_server_is_told_which_deployment_it_serves():
    assert library_client.SERVER.env["QF_HOME"] == str(ROOT)
    assert "ANTHROPIC_API_KEY" not in library_client.SERVER.env  # the server needs no key, so it gets none


def test_the_fleet_view_holds_numbers_and_ids_only(bakery):
    env = {**os.environ, "QF_HOME": str(bakery)}
    subprocess.run([sys.executable, "-m", "quizforge.fleet", "publish"], env=env, capture_output=True, check=True)
    status = json.loads((bakery / fleet.STATUS).read_text())
    assert status["name"] == "bakery" and status["lessons"] == 3 and status["prompt"] == "v5"
    assert "flour" not in json.dumps(status).lower()  # no lesson text, no question text
