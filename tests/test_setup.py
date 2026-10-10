import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = json.loads((ROOT / ".claude" / "settings.json").read_text())


def test_settings_deny_reading_env():
    deny = SETTINGS["permissions"]["deny"]
    assert "Read(./.env)" in deny and "Read(./.env.*)" in deny


def test_settings_enable_the_plugin_from_the_repo():
    assert SETTINGS["enabledPlugins"]["quiz-forge-tools@quiz-forge"] is True
    assert SETTINGS["extraKnownMarketplaces"]["quiz-forge"]["source"]["path"] == "./plugin"


def test_settings_hold_no_hooks_the_plugins_carry_them():
    assert "hooks" not in SETTINGS


def test_shared_settings_keep_manual_mode():
    assert SETTINGS["permissions"]["defaultMode"] == "default"


def test_gitignore_keeps_personal_files_and_secrets_out():
    ignored = (ROOT / ".gitignore").read_text().split()
    for name in (".env", "CLAUDE.local.md", ".claude/settings.local.json"):
        assert name in ignored


def test_claude_md_is_lean():
    lines = (ROOT / "CLAUDE.md").read_text().splitlines()
    assert len(lines) <= 40
    assert any("bank/approved/" in line for line in lines)
