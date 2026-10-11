import tomllib

from quizforge import sources, write
from quizforge.config import ROOT, load_config
from reviewer import sdk_review

POLICY = tomllib.loads((ROOT / "quizforge/security/policy.toml").read_text())


def names(tools):
    return {tool["name"] for tool in tools}


def test_the_writer_has_exactly_its_listed_tools():
    assert names(write.tools(load_config())) == set(POLICY["writer"])


def test_the_checker_has_exactly_its_listed_tools():
    assert names(sources.tools(load_config().library)) == set(POLICY["checker"])


def test_the_reviewer_is_allowed_only_its_listed_tools_and_asks_for_nothing_else():
    options = sdk_review.options()
    assert set(options.allowed_tools) == set(POLICY["reviewer"])
    assert options.permission_mode == "dontAsk" and {"Write", "Edit", "Bash"} <= set(options.disallowed_tools)
