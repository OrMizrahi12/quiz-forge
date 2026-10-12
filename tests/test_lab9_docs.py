"""Lab 9: the documents a new team and two reviewers read. They must exist and have their sections."""

import re

from quizforge.config import CODE


def text(rel):
    path = CODE / rel
    assert path.exists(), f"{rel} is missing"
    return path.read_text()


def test_the_adr_has_every_section_and_a_recheck_date():
    adr = text("docs/adr/0001-where-it-runs.md")
    for section in (
        "## Context",
        "## Options",
        "## Decision",
        "## Consequences",
        "## Security and procurement",
        "## Re-check",
    ):
        assert section in adr, f"ADR 0001 has no '{section}' section"
    recheck = adr.split("## Re-check", 1)[1]
    assert re.search(r"\b20\d\d-\d\d-\d\d\b", recheck), "the Re-check section names no date"


def test_the_readme_quickstart_covers_init_plan_and_export():
    readme = text("README.md")
    for command in ("qf init", "qf plan", "qf export", "fresh_clone_check.sh"):
        assert command in readme, f"README.md never mentions {command}"


def test_the_fresh_clone_check_exists_and_ends_with_ok():
    script = text("scripts/fresh_clone_check.sh")
    assert "fresh clone: ok" in script and "git clone" in script and "pytest" in script
