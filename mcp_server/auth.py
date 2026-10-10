"""Who may call the library over HTTP. Development only: a table of hashed local tokens.
In production, verify a JWT from your identity provider, or call its introspection endpoint."""
import hashlib
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier

RESOURCE = "http://127.0.0.1:8765/mcp"  # this server: the audience its tokens must name
HASHES = Path.home() / ".config/quiz-forge/mcp-token-hashes"  # outside the repo, mode 600


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class HashedTokenVerifier(TokenVerifier):
    def __init__(self, hashes: Path = HASHES):
        self.hashes = hashes

    async def verify_token(self, token: str) -> AccessToken | None:
        known = self.hashes.read_text().split() if self.hashes.exists() else []
        if not token or digest(token) not in known:
            return None  # the request stops at the door: 401
        return AccessToken(token=token, client_id="dev-laptop", scopes=["library:read"], resource=RESOURCE)
