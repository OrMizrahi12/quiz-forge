"""The development token check: a registered token passes, any other is refused."""
import pytest

from mcp_server.auth import RESOURCE, HashedTokenVerifier, digest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_only_the_registered_token_passes(tmp_path):
    hashes = tmp_path / "hashes"
    hashes.write_text(digest("good-token") + "\n")
    verifier = HashedTokenVerifier(hashes)
    passed = await verifier.verify_token("good-token")
    assert passed.scopes == ["library:read"] and passed.resource == RESOURCE
    assert await verifier.verify_token("another-token") is None
    assert await verifier.verify_token("") is None
