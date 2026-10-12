"""9.6: qf init makes a deployment from the template without changing the template."""

import json
import tomllib

import pytest

from quizforge.config import CODE
from quizforge.init import AUDIENCE, init
from quizforge.prompts import digest, load_prompt, locked

SAMPLE = CODE / "examples/sample-library/v1"


def test_a_deployment_has_its_own_files(tmp_path):
    folder = tmp_path / "bakery"
    init(folder, SAMPLE, "bakery", "home bakers learning to make bread")
    config = tomllib.loads((folder / "config.toml").read_text())
    assert config["deployment"]["name"] == "bakery" and config["library"]["path"] == "library"
    assert (folder / "library/MANIFEST.json").exists() and (folder / "bank/approved").is_dir()
    assert [json.loads(line)["lesson"] for line in (folder / "evals/cases.jsonl").read_text().splitlines()] == [
        "B1.1",
        "B1.2",
        "B1.3",
    ]


def test_the_audience_gets_a_new_locked_version_and_the_template_stays(tmp_path):
    before = locked(CODE / "prompts/item_writer")
    folder = tmp_path / "bakery"
    init(folder, SAMPLE, "bakery", "home bakers learning to make bread")
    version = tomllib.loads((folder / "config.toml").read_text())["prompt"]["item_writer"]
    text = load_prompt(folder / "prompts/item_writer", version)  # locked, and matches its hash
    assert "home bakers" in text and AUDIENCE not in text
    assert locked(CODE / "prompts/item_writer") == before
    assert digest((folder / "prompts/item_writer/v4.md").read_text()) == before["v4"]


def test_init_refuses_a_folder_in_use(tmp_path):
    (tmp_path / "used").mkdir()
    (tmp_path / "used/notes.txt").write_text("x")
    with pytest.raises(SystemExit):
        init(tmp_path / "used", SAMPLE, "x", "y")
