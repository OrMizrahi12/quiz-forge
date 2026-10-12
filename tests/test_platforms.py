"""The platform switch: the right client class per platform, and the gaps it reports. No request, no cloud account:
the cloud classes are replaced by stand-ins that record how they were built."""
import anthropic
import pytest

from quizforge import platforms


@pytest.fixture(autouse=True)
def dummy_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


def test_the_default_is_the_claude_api():
    assert platforms.current() == "anthropic"
    assert type(platforms.base_client()) is anthropic.Anthropic


@pytest.mark.parametrize("name", list(platforms.PLATFORMS))
@pytest.mark.parametrize("asynchronous", [False, True])
def test_each_platform_gets_its_own_client_class(monkeypatch, name, asynchronous):
    cls = ("Async" if asynchronous else "") + platforms.PLATFORMS[name]["client"]
    stand_in = type(cls, (), {})
    monkeypatch.setattr(anthropic, cls, stand_in)
    assert type(platforms.base_client(asynchronous, name=name)) is stand_in


def test_the_gaps_are_the_features_we_use():
    for name, platform in platforms.PLATFORMS.items():
        assert set(platform["missing"]) <= set(platforms.USES), name
    assert "structured_outputs" in platforms.gaps("bedrock")
    assert platforms.gaps("aws") == {} and platforms.gaps("anthropic") == {}


class Recorder:
    """A stand-in client: whatever the factory calls on it (with_options, ...) returns it again."""

    def __getattr__(self, name):
        return lambda *args, **kwargs: self


def test_the_factory_builds_through_the_platform(monkeypatch):
    from quizforge.client import make_client

    monkeypatch.setattr(platforms, "base_client", lambda asynchronous=False, name=None: Recorder())
    assert isinstance(make_client(), Recorder)
