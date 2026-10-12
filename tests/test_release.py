"""9.5: the release manifest and the upgrade rule, offline: a stand-in Models API, no requests."""

import tomllib
from datetime import date
from types import SimpleNamespace

import quizforge
from quizforge import release
from quizforge.config import ROOT

TODAY = date(2026, 10, 11)
ENTRY = {"status": "active", "retires_not_before": date(2027, 10, 7)}


def info(model, lifecycle="active", retires_at=None):
    return SimpleNamespace(id=model, lifecycle=lifecycle, retires_at=retires_at)


def test_every_configured_model_is_in_the_lock():
    config = tomllib.loads((ROOT / "config.toml").read_text())
    lock = tomllib.loads((ROOT / "models.lock.toml").read_text())
    assert set(release.features(config).values()) <= set(lock)


def test_an_alias_is_a_problem():
    status, problem = release.check("claude-haiku-4-5", ENTRY, info("claude-haiku-4-5-20251001"), TODAY)
    assert status == "alias" and "pin the snapshot" in problem


def test_a_model_missing_from_the_lock_is_a_problem():
    assert "not in models.lock.toml" in release.check("claude-new", None, info("claude-new"), TODAY)[1]


def test_deprecated_is_a_problem_and_soon_is_a_watch():
    assert release.check("m", ENTRY, info("m", "deprecated", "2026-11-30"), TODAY)[1]
    soon = {"status": "active", "retires_not_before": date(2026, 10, 15)}
    assert release.check("m", soon, info("m"), TODAY) == ("active, watch", None)
    assert release.check("m", ENTRY, info("m"), TODAY) == ("active", None)


def test_the_manifest_names_version_commit_models_and_prompts():
    client = SimpleNamespace(models=SimpleNamespace(retrieve=info))
    lines, problems = release.manifest(client, TODAY)
    assert lines[0].startswith(f"quiz-forge {quizforge.__version__} at ") and "config.toml" in lines[0]
    assert any(line.startswith("writer ") for line in lines)
    assert not any("NOT LOCKED" in line for line in lines) and problems == []


def test_the_changelog_has_this_version():
    assert f"## {quizforge.__version__} " in (ROOT / "CHANGELOG.md").read_text()

