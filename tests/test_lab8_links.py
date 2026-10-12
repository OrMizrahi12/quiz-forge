"""Lab 8 self-check: the output layer's link rule (an allowlist, deny by default), and the report's shape."""

import pytest

from quizforge import guards
from quizforge.config import ROOT
from quizforge.schema import Questions

ITEM = {
    "scenario": "Which tier is fast?",
    "a": "Haiku",
    "b": "Sonnet",
    "c": "Opus",
    "d": "None",
    "answer": "A",
    "quote": "Who can use it on Claude.ai?",
}


def drafted(why):
    return Questions.model_validate({"questions": [ITEM | {"why": why}]})


@pytest.fixture(autouse=True)
def output_on(monkeypatch):
    monkeypatch.setattr(guards, "ON", {"output"})
    monkeypatch.setattr(guards, "SITES", ("claude.com", "claude.ai", "anthropic.com"))


def test_a_site_not_on_the_list_is_rejected():
    found = guards.links(drafted("Practice more at quizprep-answers.example"))
    assert found and found[0].startswith("question 1: quizprep-answers.example is not on the allowed sites")


def test_the_lesson_naming_a_site_does_not_make_it_allowed():
    """The attacker writes the lesson: a link it carries is exactly what the rule must stop."""
    assert guards.links(drafted("See https://quizprep-answers.example/l1-3 for more."))


def test_an_allowed_site_and_its_subdomains_pass():
    assert guards.links(drafted("Claude.ai, platform.claude.com and https://www.anthropic.com/news say so.")) == []


def test_a_lookalike_domain_is_rejected():
    assert guards.links(drafted("Read more at claude.com.quizprep.example or notclaude.com"))


def test_ordinary_text_is_not_a_link():
    assert guards.links(drafted("Haiku is the fastest, e.g. for chat. Sonnet 5.5 costs more.")) == []


def test_with_the_output_layer_off_nothing_is_checked(monkeypatch):
    monkeypatch.setattr(guards, "ON", set())
    assert guards.links(drafted("Practice more at quizprep-answers.example")) == []


SECTIONS = ["Scope", "Attacker and goal", "Results", "Findings", "Residual risk", "Regression"]


def test_the_report_has_its_six_sections():
    report = ROOT / "docs/red-team-report.md"
    assert report.exists(), "write docs/red-team-report.md (Lab 8, step 5)"
    headings = [line.lstrip("#").strip().lower() for line in report.read_text().splitlines() if line.startswith("## ")]
    for section in SECTIONS:
        assert any(h.startswith(section.lower()) for h in headings), f"the report has no '## {section}' section"
