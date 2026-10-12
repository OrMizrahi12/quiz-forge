"""Lab 9: v1.0.0, and the release manifest from a deployment folder (QF_HOME), which is not a git checkout.
A stand-in Models API: no requests."""

import shutil
import tomllib
from datetime import date
from types import SimpleNamespace

import quizforge
from quizforge import release
from quizforge.config import CODE, ROOT

TODAY = date(2026, 10, 12)


def info(model):
    return SimpleNamespace(id=model, lifecycle="active", retires_at=None)


def test_the_version_is_1_0_0_and_the_changelog_says_what_changed():
    assert quizforge.__version__ == "1.0.0"
    changelog = (ROOT / "CHANGELOG.md").read_text()
    entry = changelog.split("## 1.0.0 ", 1)[1].split("\n## ", 1)[0] if "## 1.0.0 " in changelog else ""
    assert entry, "CHANGELOG.md has no ## 1.0.0 entry"
    for word in ("domain", "plan", "QF_HOME"):
        assert word in entry, f"the 1.0.0 entry doesn't mention {word}"


def test_the_manifest_runs_from_a_deployment_folder(tmp_path, monkeypatch):
    for name in ("config.toml", "models.lock.toml"):
        shutil.copy(ROOT / name, tmp_path / name)
    shutil.copytree(ROOT / "prompts", tmp_path / "prompts")
    monkeypatch.setattr(release, "ROOT", tmp_path)  # what QF_HOME=<deployment> does; tmp_path is not a checkout
    lines, problems = release.manifest(SimpleNamespace(models=SimpleNamespace(retrieve=info)), TODAY)
    assert lines[0].startswith("quiz-forge 1.0.0 at ") and problems == []


def test_the_package_version_comes_from_the_code():
    assert tomllib.loads((CODE / "pyproject.toml").read_text())["project"]["dynamic"] == ["version"]
