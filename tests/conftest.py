import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import quizforge from the project folder


def pytest_addoption(parser):
    parser.addoption("--update-snapshot", action="store_true", help="rewrite tests/snapshots from the code")


@pytest.fixture(autouse=True)
def offline(request, monkeypatch):
    """Unit, contract and functional tests never touch the network: a connection fails the test at once.
    Tests marked integration or e2e cross a boundary on purpose, so they may connect."""
    if request.node.get_closest_marker("integration") or request.node.get_closest_marker("e2e"):
        return

    def refuse(sock, address):
        pytest.fail(f"this test tried to connect to {address}: give it a fake client, or mark it", pytrace=False)

    monkeypatch.setattr(socket.socket, "connect", refuse)
