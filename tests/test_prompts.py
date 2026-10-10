import shutil

import pytest

from quizforge.config import load_config
from quizforge.prompts import PromptChanged, for_schema, load_prompt, lock, versions

CFG = load_config()


def test_versions_sort_by_number(tmp_path):
    for n in (1, 2, 10):
        (tmp_path / f"v{n}.md").write_text(f"prompt {n}")
    (tmp_path / "system.md").write_text("not a version")
    assert versions(tmp_path) == ["v1", "v2", "v10"]


def test_the_configured_version_is_locked_and_loads():
    assert CFG.prompt in versions(CFG.prompts)
    assert "<instructions>" in load_prompt(CFG.prompts, CFG.prompt)


def test_an_unknown_version_is_refused():
    with pytest.raises(ValueError, match="unknown prompt version"):
        load_prompt(CFG.prompts, "v99")


def test_an_edited_version_is_caught(tmp_path):
    folder = tmp_path / "item_writer"
    shutil.copytree(CFG.prompts, folder)
    path = folder / f"{CFG.prompt}.md"
    path.write_text(path.read_text() + "\nOne more rule.\n")
    with pytest.raises(PromptChanged):
        load_prompt(folder, CFG.prompt)


def test_a_version_loads_only_once_locked(tmp_path):
    (tmp_path / "v1.md").write_text("Rules.")
    with pytest.raises(PromptChanged):
        load_prompt(tmp_path, "v1")
    lock(tmp_path, "v1")
    assert load_prompt(tmp_path, "v1") == "Rules."
    with pytest.raises(PromptChanged):
        lock(tmp_path, "v1")  # a locked version is never locked again


def test_the_schema_replaces_the_format_section():
    text = for_schema(load_prompt(CFG.prompts, CFG.prompt))
    assert "<format>" not in text and "<instructions>" in text
