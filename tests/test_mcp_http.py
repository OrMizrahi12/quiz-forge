"""Lab 6: one build, two transports. Over HTTP every request needs a registered token (a temporary hashes file here,
never a real token); over stdio the boundary is the process that started the server."""

import pytest
from starlette.testclient import TestClient

from mcp_server import server
from mcp_server.auth import digest

INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture
def http(tmp_path):
    hashes = tmp_path / "hashes"
    hashes.write_text(digest("registered-token") + "\n")
    with TestClient(
        server.build(http=True, hashes=hashes).streamable_http_app(), base_url="http://127.0.0.1:8765"
    ) as client:
        yield client


def post(client, token=None):
    headers = dict(HEADERS, **({"Authorization": f"Bearer {token}"} if token else {}))
    return client.post("/mcp", json=INIT, headers=headers)


def test_missing_token_refused(http):
    refused = post(http)
    assert refused.status_code == 401 and "resource_metadata" in refused.headers["www-authenticate"]


def test_wrong_token_refused(http):
    assert post(http, "a-guess").status_code == 401


def test_registered_token_accepted(http):
    accepted = post(http, "registered-token")
    assert accepted.status_code == 200 and '"protocolVersion"' in accepted.text


def test_both_builds_offer_the_same_tools():
    stdio, remote = server.build(), server.build(http=True)
    assert stdio.name == remote.name == "quiz-library"
